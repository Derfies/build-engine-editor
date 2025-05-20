import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtGui import QSurfaceFormat, QOpenGLContext
# from PySide6.QtOpenGL import QOpenGLWidget, QOpenGLContext
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import GL_QUADS, GL_DEPTH_BUFFER_BIT, GL_COLOR_BUFFER_BIT, GL_DEPTH_TEST





class GLWidget(QOpenGLWidget):

    def initializeGL(self):

        self.gl = QOpenGLContext.currentContext().functions()
        print(self.gl)
        self.gl.glEnable(GL_DEPTH_TEST)
        self.gl.glClearColor(0.2, 0.2, 0.2, 1)

    def paintGL(self):
        self.gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


        #
        # self.gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # self.gl.glLoadIdentity()
        # self.gl.glTranslatef(0.0, 0.0, -5.0)
        #
        # # Draw a simple rotating cube (no rotation added here yet)
        self.gl.glBegin(GL_QUADS)
        # self.gl.glColor3f(1, 0, 0)  # Red
        # self.gl.glVertex3f(1, 1, -1)
        # self.gl.glVertex3f(-1, 1, -1)
        # self.gl.glVertex3f(-1, 1, 1)
        # self.gl.glVertex3f(1, 1, 1)
        # self.gl.glEnd()

    def resizeGL(self, w, h):
        self.gl.glViewport(0, 0, w, h)


class Window(QWidget):
    def __init__(self):
        super().__init__()
        format = QSurfaceFormat()
        format.setVersion(4, 1)
        format.setProfile(QSurfaceFormat.CoreProfile)
        format.setDepthBufferSize(24)
        format.setStencilBufferSize(8)
        QSurfaceFormat.setDefaultFormat(format)

        self.gl_widget = GLWidget()

        self.setWindowTitle("PySide6 OpenGL Example")
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.addWidget(self.gl_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())