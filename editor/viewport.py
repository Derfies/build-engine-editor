import math
import sys
import time
from dataclasses import dataclass, field

import numpy as np
from OpenGL.GL import GL_FLOAT, GL_TRIANGLES, GL_COLOR_BUFFER_BIT, GL_CULL_FACE, GL_BACK, GL_CCW, GL_CW
from PySide6.QtCore import QCoreApplication, Qt, QPoint
from PySide6.QtGui import QOpenGLFunctions, QMatrix4x4, QVector3D, QVector4D
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLBuffer, QOpenGLVertexArrayObject, QOpenGLShader
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication, QMainWindow
from shapely import Polygon
from shapely.ops import triangulate, orient

from applicationframework.document import Document
from editor.updateflag import UpdateFlag

# noinspection PyUnresolvedReferences
from __feature__ import snake_case


@dataclass
class Entity:

    position: QVector3D = field(default_factory=QVector3D)


class Mesh:

    def __init__(self, vertices: np.ndarray):
        self.vertex_count = len(vertices)
        self.vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
        self.vbo.create()
        self.vbo.bind()
        self.vbo.allocate(vertices.tobytes(), vertices.nbytes)
        self.vbo.release()

        self.vao = QOpenGLVertexArrayObject()
        self.vao.create()

    def bind(self, program):
        self.vao.bind()
        self.vbo.bind()

        program.enable_attribute_array(0)
        program.set_attribute_buffer(0, GL_FLOAT, 0, 3)

        self.vbo.release()
        self.vao.release()

    def draw(self, gl):
        self.vao.bind()
        gl.glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)
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
        self.elevation = max(0, min(89.9, self.elevation))

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

        self.meshes = []
        self.app().updated.connect(self.update_event)

    def app(self) -> QCoreApplication:
        return QApplication.instance()

    def update_event(self, doc: Document, flags: UpdateFlag):

        #from PySide6.QtGui import QOpenGLContext
        #print('-->', self.program)
        if self.program is None:
            print('early out')
            return

        #self.block_signals(True)
        if flags != UpdateFlag.SELECTION and flags != UpdateFlag.SETTINGS:

            start = time.time()

            print('FULL UPDATE')

            self.make_current()

            for mesh in self.meshes:
                mesh.delete()
            self.meshes.clear()

            try:

                for face in doc.content.faces:

                    sector = Polygon([node.pos.to_tuple() for node in face.nodes])
                    sector = orient(sector, sign=1.0)
                    triangles = triangulate(sector)

                    floor_vertices = []
                    ceiling_vertices = []
                    for tri in triangles:
                        for coord in tri.exterior.coords[:-1]:

                            # NOTE: Ratio of z axis to other axes is 16:1.
                            floor_vertices.append((coord[0], face.get_attribute('floorz') / -16, coord[1]))
                            ceiling_vertices.append((coord[0], face.get_attribute('ceilingz') / -16, coord[1]))

                    quad = Mesh(np.array(floor_vertices, dtype=np.float32))
                    quad.bind(self.program)
                    self.meshes.append(quad)

                    #print(np.array(ceiling_vertices, dtype=np.float32))
                    #print(np.array(list(reversed(ceiling_vertices)), dtype=np.float32))

                    quad2 = Mesh(np.array(list(reversed(ceiling_vertices)), dtype=np.float32))
                    quad2.bind(self.program)
                    self.meshes.append(quad2)

            except Exception as e:
                print(e)

            self.done_current()

            self.update()

            end = time.time()
            print('viewport:', end - start)

        #self.block_signals(False)

    def initializeGL(self):
        self.gl = QOpenGLFunctions(self.context())
        self.gl.initializeOpenGLFunctions()

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
                    void main() {
                        fragColor = vec4(1.0, 0.5, 0.2, 1.0);
                    }
                """)
        self.program.link()

        self.camera = OrbitCamera()
        self.last_mouse_pos = QPoint()

        self.near_plane = 0.1
        self.far_plane = 1000000.0
        self.fov = 45.0
        self.aspect_ratio = 1.0

    def resizeGL(self, w, h):
        self.aspect_ratio = w / h if h != 0 else 1.0

        self.gl.glViewport(0, 0, w, h)

    def paintGL(self):
        #print('PAINT')
        self.gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        self.gl.glClear(GL_COLOR_BUFFER_BIT)

        # Create projection matrix.
        proj = QMatrix4x4()
        proj.perspective(self.fov, self.aspect_ratio, self.near_plane, self.far_plane)
        view = self.camera.get_view_matrix()
        self.program.bind()
        self.program.set_uniform_value('mvp', proj * view)
        for mesh in self.meshes:
            #print('mesh:', mesh)
            mesh.draw(self.gl)
        self.program.release()

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
        self.camera.zoom(0.9 if event.angle_delta().y() > 0 else 1.1)
        self.update()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.set_window_title("OpenGL Triangle")
        self.set_central_widget(Viewport())
        self.resize(600, 600)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
