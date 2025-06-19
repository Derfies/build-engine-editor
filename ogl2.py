import math
import sys
from dataclasses import dataclass, field

import numpy as np
from OpenGL.GL import GL_FLOAT, GL_TRIANGLES, GL_COLOR_BUFFER_BIT, GL_CULL_FACE, GL_BACK, GL_CCW, GL_CW
from PySide6.QtCore import QCoreApplication, Qt, QPoint
from PySide6.QtGui import QOpenGLFunctions, QMatrix4x4, QVector3D
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
        self.sensitivity = 0.5

    def orbit(self, delta: QPoint):
        self.azimuth -= delta.x() * self.sensitivity
        self.elevation += delta.y() * self.sensitivity
        self.elevation = max(0, min(89.9, self.elevation))

    def zoom(self, factor: float):
        self.distance *= factor#
        self.distance = max(1.0, min(10000.0, self.distance))

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


class TriangleWidget(QOpenGLWidget):

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

            self.make_current()

            for mesh in self.meshes:
                mesh.delete()
            self.meshes.clear()

            for face in doc.content.faces:

                sector = Polygon([node.pos.to_tuple() for node in face.nodes])
                sector = orient(sector, sign=1.0)
                triangles = triangulate(sector)

                vertices = []
                for tri in triangles:
                    for coord in tri.exterior.coords[:-1]:
                        vertices.append((coord[0], 0, coord[1]))

                v = np.array(vertices, dtype=np.float32)


                quad = Mesh(v)
                quad.bind(self.program)
                self.meshes.append(quad)

            self.done_current()


            self.update()

        # for mesh in self.meshes:
        #     print(mesh)


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
        if event.buttons() & Qt.LeftButton:
            self.last_mouse_pos = event.position().to_point()

    def mouse_move_event(self, event):
        if event.buttons() & Qt.LeftButton:
            delta = event.position().to_point() - self.last_mouse_pos
            self.camera.orbit(delta)
            self.last_mouse_pos = event.position().to_point()
            self.update()

    def wheel_event(self, event):
        self.camera.zoom(0.9 if event.angle_delta().y() > 0 else 1.1)
        self.update()


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.set_window_title("OpenGL Triangle")
        self.set_central_widget(TriangleWidget())
        self.resize(600, 600)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
