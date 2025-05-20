import sys
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow#, QOpenGLWidget
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtCore import Qt
from OpenGL.GL import *
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader, QOpenGLBuffer, QOpenGLVertexArrayObject


class TriangleWidget(QOpenGLWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setProfile(QSurfaceFormat.CoreProfile)
        fmt.setVersion(3, 3)
        self.setFormat(fmt)

        self.program = None
        self.vbo = QOpenGLBuffer()
        self.vao = QOpenGLVertexArrayObject()

    def initializeGL(self):
        #self.initializeOpenGLFunctions()

        # Define vertex data (x, y)
        vertices = np.array([
            -0.5, -0.5,
             0.5, -0.5,
             0.0,  0.5,
        ], dtype=np.float32)

        # Compile shaders
        vertex_src = """
        #version 330 core
        layout(location = 0) in vec2 position;
        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
        }
        """
        fragment_src = """
        #version 330 core
        out vec4 fragColor;
        void main() {
            fragColor = vec4(0.2, 0.8, 0.4, 1.0);
        }
        """
        self.program = QOpenGLShaderProgram()
        self.program.addShaderFromSourceCode(QOpenGLShader.Vertex, vertex_src)
        self.program.addShaderFromSourceCode(QOpenGLShader.Fragment, fragment_src)
        self.program.link()

        # Set up VAO
        self.vao.create()
        self.vao.bind()

        # Set up VBO
        self.vbo.create()
        self.vbo.bind()
        self.vbo.allocate(vertices.tobytes(), vertices.nbytes)

        self.program.bind()
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)
        self.vbo.release()
        self.vao.release()
        self.program.release()

    def paintGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        self.program.bind()
        self.vao.bind()
        glDrawArrays(GL_TRIANGLES, 0, 3)
        self.vao.release()
        self.program.release()

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt Modern OpenGL Triangle")
        self.setCentralWidget(TriangleWidget(self))
        self.resize(800, 600)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())