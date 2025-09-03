import math
import time
import traceback
from dataclasses import dataclass, field

import numpy as np
from OpenGL.GL import (
    GL_BACK,
    GL_COLOR_BUFFER_BIT,
    GL_CULL_FACE,
    GL_CW,
    GL_DEPTH_TEST,
    GL_FLOAT,
    GL_TRIANGLES,
)
from PySide6.QtCore import QCoreApplication, Qt, QPoint
from PySide6.QtGui import QOpenGLFunctions, QMatrix4x4, QVector3D, QVector4D
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLBuffer, QOpenGLVertexArrayObject, QOpenGLShader
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication, QGraphicsItem
from shapely import Polygon
from shapely.ops import orient

from applicationframework.document import Document
from editor import utils
from editor.graph import Face, Ring
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


@dataclass
class Entity:

    # TODO: Deprecate

    position: QVector3D = field(default_factory=QVector3D)


class Mesh:

    def __init__(self, vertices: np.ndarray, shade: float = 1.0):
        self.vertices = vertices
        self.shade = shade


class MeshPool:

    def __init__(self):
        self.meshes = []

        self.vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self.vbo.create()

        self.vao = QOpenGLVertexArrayObject()
        self.vao.create()

    def allocate(self):

        # TODO: Need to be able to derive len of vertices without writing to .vertices
        self.vertices = np.vstack([m.vertices for m in self.meshes])

        self.vbo.bind()
        self.vbo.allocate(self.vertices.tobytes(), self.vertices.nbytes)
        self.vbo.release()

    def draw(self, gl, program):

        # TODO: Not sure who needs to know about program...
        if not hasattr(self, 'vertices'):
            return

        self.vao.bind()
        self.vbo.bind()

        program.enable_attribute_array(0)
        program.set_attribute_buffer(0, GL_FLOAT, 0, 3)

        self.vbo.release()

        offset = 0
        for mesh in self.meshes:
            loc = program.uniform_location('shade')
            program.set_uniform_value1f(loc, mesh.shade)
            gl.glDrawArrays(GL_TRIANGLES, offset, len(mesh.vertices))
            offset += len(mesh.vertices)
        self.vao.release()

    def delete(self):
        if self.vbo.is_created():
            self.vbo.destroy()
        if self.vao.is_created():
            self.vao.delete_later()  # or `.destroy()` depending on Qt version


class OrbitCamera:

    def __init__(self):
        super().__init__()
        self.azimuth = 0
        self.elevation = 45.0
        self.distance = 10000.0
        self.target = Entity()

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
        ) + self.target.position
        up = QVector3D(0, 1, 0)
        view = QMatrix4x4()
        view.look_at(eye, self.target.position, up)
        return view


class Viewport(QOpenGLWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.program = None

        self.mesh_pool = None
        self.app().updated.connect(self.update_event)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    @staticmethod
    def create_wall_mesh(xz1: tuple[float, float], y1: float, xz2: tuple[float, float], y2: float, shade: float) -> Mesh:
        x1, z1 = xz1
        x2, z2 = xz2
        wall_vertices = [

            # Bottom left.
            [x1, y1, z1],
            [x1, y2, z1],
            [x2, y1, z2],

            # Top right.
            [x1, y2, z1],
            [x2, y2, z2],
            [x2, y1, z2],
        ]
        return Mesh(np.array(wall_vertices, dtype=np.float32), shade=shade)

    def build_ring(self, ring: Ring, coords: tuple[tuple[float, float]], y1: float, y2: float):
        for i in range(len(coords) - 1):
            edge = ring.edges[i]
            # wall_shade = build_shade_to_brightness(edge.get_attribute('shade'))
            wall_shade = edge.get_attribute('shade')

            # If there is no connected face, draw the wall from floor to ceiling.
            # If there is a connected face and the floor is lower than ours, dont draw it.
            # If there is a connected face and the ceiling is higher than ours, don't draw it.

            connected_face = None
            rev_edge = edge.reversed
            if rev_edge is not None:
                connected_face = rev_edge.face

            xz0, xz1 = coords[i], coords[i + 1]
            if connected_face is None:
                self.mesh_pool.meshes.append(self.create_wall_mesh(xz0, y1, xz1, y2, wall_shade))
            else:
                y3 = connected_face.get_attribute('floorz')# / -16
                y4 = connected_face.get_attribute('ceilingz')# / -16
                if y1 < y3:
                    self.mesh_pool.meshes.append(self.create_wall_mesh(xz0, y1, xz1, y3, wall_shade))
                if y2 > y4:
                    self.mesh_pool.meshes.append(self.create_wall_mesh(xz0, y4, xz1, y2, wall_shade))

            i += 1

    def update_event(self, doc: Document, flags: UpdateFlag):

        if self.program is None:
            print('early out')
            return

        #self.block_signals(True)
        #start = time.time()
        if flags != UpdateFlag.SELECTION and flags != UpdateFlag.SETTINGS:

            print('FULL UPDATE')

            self.make_current()

            if self.mesh_pool is not None:
                self.mesh_pool.delete()
            self.mesh_pool = MeshPool()

            try:

                for face in doc.content.faces:

                    y1 = face.get_attribute('floorz')
                    y2 = face.get_attribute('ceilingz')
                    floor_shade = face.get_attribute('floorshade')
                    ceiling_shade = face.get_attribute('ceilingshade')

                    ring_positions = [
                        [node.pos.to_tuple() for node in ring.nodes]
                        for ring in face.rings
                    ]
                    try:
                        sector = Polygon(ring_positions[0], [list(reversed(ring)) for ring in ring_positions[1:]])
                    except Exception as e:
                        traceback.print_exc()

                    # TODO: Still some invalid polys.
                    try:
                        triangles = utils.triangulate_polygon(sector)
                    except Exception as e:
                        traceback.print_exc()
                        continue

                    floor_vertices = []
                    ceiling_vertices = []
                    for tri in triangles:
                        for coord in tri.exterior.coords[:-1]:

                            # NOTE: Ratio of z axis to other axes is 16:1.
                            floor_vertices.append((coord[0], y1, coord[1]))
                            ceiling_vertices.append((coord[0], y2, coord[1]))

                    self.mesh_pool.meshes.append(Mesh(np.array(floor_vertices, dtype=np.float32), shade=floor_shade))
                    self.mesh_pool.meshes.append(Mesh(np.array(ceiling_vertices[::-1], dtype=np.float32), shade=ceiling_shade))

                    # Do walls.
                    self.build_ring(face.rings[0], tuple(sector.exterior.coords), y1, y2)
                    for i, interior in enumerate(sector.interiors):
                        self.build_ring(face.rings[i + 1], tuple(reversed(interior.coords)), y1, y2)

                self.mesh_pool.allocate()

            except Exception as e:
                traceback.print_exc()

            self.done_current()

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

        self.program = QOpenGLShaderProgram()
        self.program.add_shader_from_source_code(QOpenGLShader.Vertex, """
            #version 330
            layout(location = 0) in vec3 position;
            uniform mat4 mvp;
            void main() {
                gl_Position = mvp * vec4(position, 1.0);
            }
        """)
        self.program.add_shader_from_source_code(QOpenGLShader.Fragment, """
            #version 330
            out vec4 fragColor;
            uniform float shade;
            void main() {
                fragColor =  vec4(vec3(1.0, 0.5, 0.2) * shade, 1.0);
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
            self.camera.target.position += v4_transformed.to_vector3_d()
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

        # TODO: Doesn't make much sense to take graphics items as the arg.
        # TODO: This is almost copy-pasted from drawing sectors above. If we
        # keep a map of graph elements to meshes we probably wont need this, and
        # then walls etc should work ootb.
        vertices = []
        for item in items:

            # TODO: How do we frame edges, etc?
            if not isinstance(item.element(), Face):
                continue
            face = item.element()
            y1 = face.get_attribute('floorz')

            rings = []
            for ring in face.rings:
                rings.append([node.pos.to_tuple() for node in ring.nodes])

            sector = Polygon(rings[0], [list(reversed(ring)) for ring in rings[1:]])
            sector = orient(sector, sign=1.0)
            triangles = utils.triangulate_polygon(sector)

            for tri in triangles:
                for coord in tri.exterior.coords[:-1]:
                    vertices.append((coord[0], y1, coord[1]))

        center, radius = utils.compute_bounding_sphere(vertices)
        dist = utils.camera_distance(radius, self.fov)
        self.camera.target.position = QVector3D(*center)
        self.camera.distance = dist
        self.update()
