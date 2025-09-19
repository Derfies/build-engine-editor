import logging
import math
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from OpenGL.GL import (
    GL_BACK,
    GL_COLOR_BUFFER_BIT,
    GL_CULL_FACE,
    GL_CW,
    GL_DEPTH_TEST,
    GL_FLOAT,
    GL_TEXTURE0,
    GL_TRIANGLES,
)
from PySide6.QtCore import QCoreApplication, Qt, QPoint
from PySide6.QtGui import QImage, QOpenGLFunctions, QMatrix4x4, QVector3D, QVector4D
from PySide6.QtOpenGL import QOpenGLTexture, QOpenGLShaderProgram, QOpenGLBuffer, QOpenGLVertexArrayObject, QOpenGLShader
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication, QGraphicsItem
from shapely import Polygon

import editor
from applicationframework.document import Document
from editor import utils
from editor.graph import Edge
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


logger = logging.getLogger(__name__)


@dataclass
class Mesh:

    positions: np.ndarray
    texcoords: np.ndarray
    texture: QOpenGLTexture
    shade: float = 1.0


class MeshPool:

    def __init__(self):
        self.meshes = []
        self._vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self._vbo.create()
        self._vao = QOpenGLVertexArrayObject()
        self._vao.create()

    def allocate(self):

        if not self.meshes:
            return

        # TODO: Need to be able to derive len of vertices without writing to .vertices
        self.vertices = np.vstack([
            np.hstack((m.positions, m.texcoords))
            for m in self.meshes
        ])

        self._vbo.bind()
        self._vbo.allocate(self.vertices.tobytes(), self.vertices.nbytes)
        self._vbo.release()

    def draw(self, gl, program):

        if not self.meshes:
            return

        # TODO: Not sure who needs to know about program...
        if not hasattr(self, 'vertices'):
            print('NO VERTS')
            return

        self._vao.bind()
        self._vbo.bind()

        stride = 5 * self.vertices.itemsize  # 5 floats per vertex

        program.enable_attribute_array(0)
        program.set_attribute_buffer(0, GL_FLOAT, 0, 3, stride)

        program.enable_attribute_array(1)  # location 1
        program.set_attribute_buffer(1, GL_FLOAT, 3 * self.vertices.itemsize, 2, stride)

        self._vbo.release()

        offset = 0
        for mesh in self.meshes:
            program.set_uniform_value1f(program.uniform_location('shade'), mesh.shade)
            mesh.texture.bind()
            program.set_uniform_value(program.uniform_location('tex'), 0)
            gl.glDrawArrays(GL_TRIANGLES, offset, len(mesh.positions))
            offset += len(mesh.positions)
            mesh.texture.release()
        self._vao.release()

    def delete(self):
        if self._vbo.is_created():
            self._vbo.destroy()
        if self._vao.is_created():
            self._vao.delete_later()  # or `.destroy()` depending on Qt version


class OrbitCamera:

    def __init__(self):
        super().__init__()
        self.azimuth = 0
        self.elevation = 45.0
        self.distance = 10000.0
        self.target = QVector3D()

    def orbit(self, delta: QPoint):
        self.azimuth -= delta.x()
        self.elevation += delta.y()
        self.elevation = max(-89.9, min(89.9, self.elevation))

    def zoom(self, factor: float):
        self.distance *= factor
        #self.distance = max(1.0, min(10000.0, self.distance))

    def get_view_matrix(self):
        az = math.radians(self.azimuth)
        el = math.radians(self.elevation)
        eye = QVector3D(
            self.distance * math.cos(el) * math.sin(az),
            self.distance * math.sin(el),
            self.distance * math.cos(el) * math.cos(az),
        ) + self.target
        up = QVector3D(0, 1, 0)
        view = QMatrix4x4()
        view.look_at(eye, self.target, up)
        return view


class Viewport(QOpenGLWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.program = None
        self.default_texture = None
        self.textures = {}

        self.mesh_pool = None
        self.app().updated.connect(self.update_event)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def get_texture(self, name: str):
        return self.textures.get(name, self.default_texture)

    @staticmethod
    def create_wall_mesh(xz1: tuple[float, float], y1: float, xz2: tuple[float, float], y2: float, texture: QOpenGLTexture, shade: float) -> Mesh:
        x1, z1 = xz1
        x2, z2 = xz2
        positions = np.array([

            # Bottom left.
            [x1, y1, z1],
            [x1, y2, z1],
            [x2, y1, z2],

            # Top right.
            [x1, y2, z1],
            [x2, y2, z2],
            [x2, y1, z2],
        ], dtype=np.float32)
        texcoords = np.array([

            # Bottom left.
            [0, 0],
            [0, 1],
            [1, 0],

            # Top right.
            [0, 1],
            [1, 1],
            [1, 0],
        ], dtype=np.float32)
        return Mesh(positions, texcoords, texture, shade=shade)

    def build_wall(self, edge: Edge, y1: int, y2: int):
        """
        If there is no connected face, draw the wall from floor to ceiling.
        If there is a connected face and their floor is lower than ours, dont draw it.
        If there is a connected face and their ceiling is higher than ours, don't draw it.

        """
        # Note sure if Build puts its MID on lower or upper...
        # TODO: Draw the full wall regardless of connected rooms if it has a mid
        # texture.
        attrs = edge.get_attributes()
        low_tex = self.get_texture(attrs['low_tex'].value)
        mid_tex = self.get_texture(attrs['mid_tex'].value)
        top_tex = self.get_texture(attrs['top_tex'].value)

        reversed_face = edge.reversed_face
        xz0 = edge.head.get_attribute('x'), edge.head.get_attribute('y')
        xz1 = edge.tail.get_attribute('x'), edge.tail.get_attribute('y')
        if reversed_face is None:
            self.mesh_pool.meshes.append(self.create_wall_mesh(xz0, y1, xz1, y2, mid_tex, attrs['shade']))
        else:
            y3 = reversed_face.get_attribute('floorz')
            y4 = reversed_face.get_attribute('ceilingz')
            if y1 < y3:
                self.mesh_pool.meshes.append(self.create_wall_mesh(xz0, y1, xz1, y3, low_tex, attrs['shade']))
            if y2 > y4:
                self.mesh_pool.meshes.append(self.create_wall_mesh(xz0, y4, xz1, y2, top_tex, attrs['shade']))

    def build_textures(self):
        logger.info('Rebuilding OpenGL textures...')
        start = time.time()
        self.textures.clear()
        for key, img in self.app().adaptor_manager.current_adaptor.images.items():
            #img = QImage(raw, raw.shape[1], raw.shape[0], 3 * raw.shape[1], QImage.Format_RGB888).mirrored()
            texture = QOpenGLTexture(img.mirrored())
            texture.set_minification_filter(QOpenGLTexture.Nearest)
            texture.set_magnification_filter(QOpenGLTexture.Nearest)
            self.textures[key] = texture
        logger.info(f'Rebuilt OpenGL textures in {time.time() - start}s')

    def update_event(self, doc: Document, flags: UpdateFlag):

        # TODO: Consider never setting adaptor to None but instead using a default adaptor to house the default texture?
        if UpdateFlag.ADAPTOR_TEXTURES in flags and self.app().adaptor_manager.current_adaptor != None:
            self.build_textures()

        if self.program is None:
            print('early out')
            return

        #self.block_signals(True)
        #start = time.time()
        if flags != UpdateFlag.SELECTION and flags != UpdateFlag.SETTINGS:

            logger.info('Rebuilding OpenGL meshes...')
            start = time.time()
            poly_duration = 0
            triangulate_duration = 0
            wall_duration = 0
            sector_duration = 0
            allocate_duration = 0

            self.make_current()

            mesh_pool_start = time.time()
            if self.mesh_pool is not None:
                self.mesh_pool.delete()
            self.mesh_pool = MeshPool()
            mesh_pool_duration = time.time() - mesh_pool_start

            try:

                for face in doc.content.faces:

                    poly_start = time.time()

                    ring_positions = [
                        [node.pos.to_tuple() for node in ring.nodes]
                        for ring in face.rings
                    ]
                    try:
                        sector = Polygon(ring_positions[0], [list(reversed(ring)) for ring in ring_positions[1:]])
                    except Exception as e:
                        traceback.print_exc()

                    poly_duration += time.time() - poly_start

                    # TODO: Still some invalid polys.
                    try:
                        tri_start = time.time()
                        tris = utils.triangulate_polygon(sector)
                        triangulate_duration += time.time() - tri_start
                    except Exception as e:
                        traceback.print_exc()
                        continue

                    sector_start = time.time()

                    attrs = face.get_attributes()
                    floor_tex = self.get_texture(attrs['floor_tex'].value)
                    ceil_tex = self.get_texture(attrs['ceiling_tex'].value)
                    positions = np.array([coord for tri in tris for coord in tri.exterior.coords[:-1]], dtype=np.float32)
                    floor_positions = np.insert(positions, 1, attrs['floorz'], axis=1)
                    ceiling_positions = np.insert(positions, 1, attrs['ceilingz'], axis=1)[::-1]
                    self.mesh_pool.meshes.append(Mesh(floor_positions, positions / 1000, floor_tex, shade=attrs['floorshade']))
                    self.mesh_pool.meshes.append(Mesh(ceiling_positions, positions[::-1] / 1000, ceil_tex, shade=attrs['ceilingshade']))
                    sector_duration += time.time() - sector_start

                    # Build walls.
                    wall_start = time.time()
                    for ring in face.rings:
                        for edge in ring.edges:
                            self.build_wall(edge, attrs['floorz'], attrs['ceilingz'])
                    wall_duration += time.time() - wall_start

                allocate_start = time.time()
                self.mesh_pool.allocate()
                allocate_duration += time.time() - allocate_start

            except Exception as e:
                traceback.print_exc()

            self.done_current()

            logger.info(f'Rebuilt OpenGL meshes in {time.time() - start}s')
            logger.debug(f'    Polygon: {poly_duration}s')
            logger.debug(f'    Triangulate: {triangulate_duration}s')
            logger.debug(f'    Walls: {wall_duration}s')
            logger.debug(f'    Sectors: {sector_duration}s')
            logger.debug(f'    Allocate: {allocate_duration}s')
            logger.debug(f'    Mesh pool destroy: {mesh_pool_duration}s')
            logger.debug(f'    Total: {poly_duration + triangulate_duration + wall_duration + sector_duration + allocate_duration + mesh_pool_duration}s')

            self.update()

        #end = time.time()
        #print('viewport:', end - start)

        #self.block_signals(False)

    def initializeGL(self):
        self.gl = QOpenGLFunctions(self.context())
        self.gl.initializeOpenGLFunctions()

        self.gl.glEnable(GL_DEPTH_TEST)
        self.gl.glEnable(GL_CULL_FACE)
        self.gl.glCullFace(GL_BACK)
        self.gl.glFrontFace(GL_CW)

        # Load texture.
        # TODO: Expose via preferences.
        default_img = QImage(Path(editor.__file__).parent.joinpath('data/textures/grid_blue_512x512.png')).mirrored()
        self.default_texture = QOpenGLTexture(default_img)

        self.program = QOpenGLShaderProgram()
        self.program.add_shader_from_source_code(QOpenGLShader.Vertex, """
            #version 330 core

            layout(location = 0) in vec3 position;   // vertex position
            layout(location = 1) in vec2 texcoord;   // texture coordinates
            
            uniform mat4 mvp;                        // model-view-projection matrix
            
            out vec2 texcoord_out;                   // pass to fragment shader
            
            void main()
            {
                gl_Position = mvp * vec4(position, 1.0);
                texcoord_out = texcoord;
            }
        """)
        self.program.add_shader_from_source_code(QOpenGLShader.Fragment, """
            #version 330 core

            in vec2 texcoord_out;         // interpolated texcoords from vertex shader
            out vec4 frag_color;           // final fragment output
            
            uniform sampler2D tex;        // bound texture
            uniform float shade;      // tint / multiplier
            
            void main()
            {
                vec4 sampled = texture(tex, texcoord_out);
                frag_color = sampled * shade;
            }
        """)
        self.program.link()

        self.camera = OrbitCamera()
        self.last_mouse_pos = QPoint()

        self.near_plane = 1
        self.far_plane = 1000000.0
        self.fov = 45.0
        self.aspect_ratio = 1.0

    def resizeGL(self, w, h):
        self.aspect_ratio = w / h if h != 0 else 1.0

        self.gl.glViewport(0, 0, w, h)

    def paintGL(self):
        #start = time.time()
        #print('PAINT')
        self.gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        self.gl.glClear(GL_COLOR_BUFFER_BIT)
        self.gl.glActiveTexture(GL_TEXTURE0)

        # Create projection matrix.
        proj = QMatrix4x4()
        proj.perspective(self.fov, self.aspect_ratio, self.near_plane, self.far_plane)
        view = self.camera.get_view_matrix()
        self.program.bind()
        self.program.set_uniform_value('mvp', proj * view)

        if self.mesh_pool is not None:
            self.mesh_pool.draw(self.gl, self.program)

        self.program.release()

        #end = time.time()
        #print('viewport:', end - start)

    def mouse_press_event(self, event):
        self.last_mouse_pos = event.position().to_point()

    def mouse_move_event(self, event):
        delta = event.position().to_point() - self.last_mouse_pos

        delta *= 0.5
        if event.buttons() & Qt.LeftButton:
            self.camera.orbit(delta)

        elif event.buttons() & Qt.MiddleButton:

            # TODO: Move to camera class.
            # TODO: Adjust by distance to target.

            # Input: rotation angles in radians
            rx_rad = math.radians(self.camera.azimuth)
            ry_rad = math.radians(self.camera.elevation)

            # Convert to degrees because QMatrix4x4.rotate expects degrees
            rx_deg = math.degrees(rx_rad)
            ry_deg = math.degrees(ry_rad)

            # Original vector
            v4 = QVector4D(-delta.x(), delta.y(), 0, 1.0) * self.camera.distance / 1000

            # Create transformation matrix
            transform = QMatrix4x4()
            transform.rotate(rx_deg, 0, 1, 0)
            transform.rotate(ry_deg, -1, 0, 0)

            # Transform the vector.
            v4_transformed = transform.map(v4)

            # Convert back to QVector3D.
            self.camera.target += v4_transformed.to_vector3_d()
            #self.update()

        elif event.buttons() & Qt.RightButton:

            # TODO: Adjust by distance to target.
            factor = 1
            if delta.x() > 0:
                factor = 0.9
            elif delta.x() < 0:
                factor = 1.1
            self.camera.zoom(factor)

        self.update()
        self.last_mouse_pos = event.position().to_point()

    def wheel_event(self, event):
        factor = 0.9 if event.angle_delta().y() > 0 else 1.1
        self.camera.zoom(factor)
        self.update()

    def frame(self, items: list[QGraphicsItem]):

        if not items:
            return

        vertices = []
        for item in items:
            element = item.element()
            for face in element.faces:
                for node in element.nodes:
                    vertices.extend(
                        (
                            (node['x'], face['floorz'], node['y']),
                            (node['x'], face['ceilingz'], node['y']),
                        )
                    )

        center, radius = utils.compute_bounding_sphere(vertices)
        dist = utils.camera_distance(radius, self.fov)
        self.camera.target = QVector3D(*center)
        self.camera.distance = dist
        self.update()
