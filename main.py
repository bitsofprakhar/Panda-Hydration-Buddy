import sys
import math
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, 
    QSystemTrayIcon, QMenu, QGraphicsDropShadowEffect, QFrame
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, 
    QSequentialAnimationGroup, QParallelAnimationGroup, QRect, 
    pyqtProperty, pyqtSignal, QObject
)
from PyQt5.QtGui import QIcon, QPainter, QColor, QPen, QPixmap, QPainterPath

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------
APP_NAME = "Panda Drink Water"
# NORMAL_INTERVAL_MS = 30 * 60 * 1000  # 30 Minutes
NORMAL_INTERVAL_MS = 5000 # Testing

REMINDER_MESSAGE = "Did you drink water? \U0001F4A7"

POPUP_STYLESHEET = """
QFrame#popup_frame {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #ddd;
}
QLabel {
    color: #333;
    font-size: 16px;
    font-weight: 700;
}
QPushButton {
    background-color: #27ae60;
    color: white;
    border-radius: 6px;
    padding: 10px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2ecc71;
}
QPushButton:disabled {
    background-color: #bdc3c7;
}
"""

class StateSignalBus(QObject):
    start_walk_in = pyqtSignal()
    arrived_at_center = pyqtSignal()
    interaction_start = pyqtSignal()
    interaction_done = pyqtSignal()
    walk_out_finished = pyqtSignal()

# -----------------------------------------------------------------------------
# PANDA CHARACTER (V9 - Winking Chibi + Scaled & Aligned)
# -----------------------------------------------------------------------------
class PandaCharacterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(240, 240) # Keep canvas size, scaling internal
        
        # Properties
        self._leg_angle = 0.0
        self._body_bounce = 0.0
        self._view_angle = 0.0
        self._arm_angle = 0.0
        self._facing_right = False 
        self._smiling = False

    # --- QProperties ---
    @pyqtProperty(float)
    def legAngle(self): return self._leg_angle
    @legAngle.setter
    def legAngle(self, val):
        self._leg_angle = val
        self.update()

    @pyqtProperty(float)
    def bodyBounce(self): return self._body_bounce
    @bodyBounce.setter
    def bodyBounce(self, val):
        self._body_bounce = val
        self.update()

    @pyqtProperty(float)
    def viewAngle(self): return self._view_angle
    @viewAngle.setter
    def viewAngle(self, val):
        self._view_angle = val
        self.update()

    @pyqtProperty(float)
    def armAngle(self): return self._arm_angle
    @armAngle.setter
    def armAngle(self, val):
        self._arm_angle = val
        self.update()

    def setFacingRight(self, val):
        self._facing_right = val
        self.update()
    
    def setSmiling(self, val):
        self._smiling = val
        self.update()

    # --- Paint Event (V9 Winking Chibi) ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # VISUAL POLISH 1: GLOBAL SCALING (Fixes "Too Large")
        SCALE_FACTOR = 0.85
        
        # Apply Scale anchored at center-bottom
        cx_root = self.width() / 2
        cy_root = self.height()
        painter.translate(cx_root, cy_root)
        painter.scale(SCALE_FACTOR, SCALE_FACTOR)
        painter.translate(-cx_root, -cy_root)
        
        # Logic coords (Before scaling)
        cx = cx_root
        cy = cy_root - 10
        
        # Colors (Dark Grey / White)
        c_white = QColor(255, 255, 255)
        c_grey = QColor(60, 60, 60)     # Dark Grey Limbs/Ears
        c_black = QColor(10, 10, 10)    # Pupils/Nose
        c_pink = QColor(255, 160, 170)  # Cheeks/Mouth
        
        # -- Helpers --
        def draw_leg(x, y, angle):
            painter.save()
            painter.translate(x, y)
            painter.rotate(angle)
            painter.setBrush(c_grey)
            painter.setPen(Qt.NoPen)
            # Stubby Chibi Leg
            painter.drawEllipse(QRect(-12, 0, 24, 34)) 
            painter.restore()

        def draw_arm_profile(x, y, angle):
            painter.save()
            painter.translate(x, y)
            painter.rotate(angle)
            painter.setBrush(c_grey)
            painter.setPen(Qt.NoPen) 
            painter.drawEllipse(QRect(-10, 0, 20, 35))
            painter.restore()

        bounce_y = cy - self._body_bounce
        
        if self._view_angle < 0.5:
            # --- PROFILE VIEW (Walking - Winking Chibi) ---
            
            painter.save()
            if self._facing_right:
                painter.translate(self.width(), 0)
                painter.scale(-1, 1) 
                cx = self.width() / 2 
            
            # 1. Far Leg
            draw_leg(cx + 6, bounce_y - 20, -self._leg_angle)
            
            # 2. Body (Tiny)
            painter.setBrush(c_white)
            painter.setPen(QPen(c_black, 2)) # Outline
            painter.save()
            painter.translate(cx, bounce_y - 25)
            painter.rotate(10)
            painter.drawEllipse(QRect(-28, -35, 56, 60))
            painter.restore()
            
            # 3. Near Leg
            draw_leg(cx - 6, bounce_y - 20, self._leg_angle)
            
            # 4. Head (Big Squircle)
            head_x, head_y = cx + 5, bounce_y - 75
            
            # Ears (Dark Grey)
            painter.setPen(Qt.NoPen)
            painter.setBrush(c_grey)
            painter.drawEllipse(int(head_x - 18), int(head_y - 12), 22, 22)
            painter.drawEllipse(int(head_x + 10), int(head_y - 12), 22, 22)
            
            # Head Base
            painter.setBrush(c_white)
            painter.setPen(QPen(c_black, 2))
            painter.drawEllipse(QRect(int(head_x - 42), int(head_y), 84, 75))
            
            # Profile Face
            # Grey Patch
            painter.setPen(Qt.NoPen)
            painter.setBrush(c_grey)
            painter.drawEllipse(int(head_x + 6), int(head_y + 25), 18, 22)
            
            # Eye (Black Pupil)
            painter.setBrush(c_black)
            painter.drawEllipse(int(head_x + 15), int(head_y + 30), 6, 6)
            
            # Cheek
            painter.setBrush(c_pink)
            painter.drawEllipse(int(head_x + 18), int(head_y + 45), 10, 6)
            
            # Nose
            painter.setBrush(c_black)
            painter.drawEllipse(int(head_x + 38), int(head_y + 42), 6, 4)
            
            # Arm
            painter.setBrush(c_grey)
            draw_arm_profile(cx + 8, bounce_y - 45, -self._leg_angle * 0.8)
            
            painter.restore()
            
        else:
            # --- FRONT VIEW (Interaction - Winking Chibi) ---
            
            # Legs
            draw_leg(cx - 15, bounce_y - 20, 0)
            draw_leg(cx + 15, bounce_y - 20, 0)
            
            # Body (Small Round)
            painter.setBrush(c_white)
            painter.setPen(QPen(c_black, 2))
            painter.drawEllipse(QRect(int(cx - 32), int(bounce_y - 65), 64, 70))
            
            # Belly X (Navel - from image)
            painter.setPen(QPen(c_black, 2))
            painter.drawLine(int(cx - 3), int(bounce_y - 20), int(cx + 3), int(bounce_y - 14))
            painter.drawLine(int(cx + 3), int(bounce_y - 20), int(cx - 3), int(bounce_y - 14))
            
            # Head (Big Squircle)
            head_y = bounce_y - 95
            
            # Ears
            painter.setPen(Qt.NoPen)
            painter.setBrush(c_grey)
            painter.drawEllipse(int(cx - 48), int(head_y + 2), 28, 28)
            painter.drawEllipse(int(cx + 20), int(head_y + 2), 28, 28)
            # Hair Tuft
            painter.setPen(QPen(c_black, 2))
            painter.drawArc(int(cx - 5), int(head_y - 5), 10, 10, 60*16, 120*16)
            
            # Head Base
            painter.setBrush(c_white)
            painter.setPen(QPen(c_black, 2))
            painter.drawEllipse(QRect(int(cx - 50), int(head_y), 100, 85))
            
            # -- FACE DETAILS (Winking) --
            
            # Left Eye (Open with Grey Patch)
            painter.setPen(Qt.NoPen)
            painter.setBrush(c_grey)
            painter.drawEllipse(int(cx - 38), int(head_y + 25), 26, 30) # Patch
            painter.setBrush(c_black) # Pupil
            painter.drawEllipse(int(cx - 28), int(head_y + 35), 8, 8) 
            # Eyebrow
            painter.setPen(QPen(c_black, 2))
            painter.drawArc(int(cx - 35), int(head_y + 20), 20, 10, 30*16, 120*16)
            
            # Right Eye (Winking with Grey Patch)
            painter.setPen(Qt.NoPen)
            painter.setBrush(c_grey)
            painter.drawEllipse(int(cx + 12), int(head_y + 25), 26, 30) # Patch
            # Wink Line
            painter.setPen(QPen(c_black, 3))
            painter.setBrush(Qt.NoBrush)
            # > shape wink
            path = QPainterPath()
            path.moveTo(cx + 18, head_y + 40)
            path.lineTo(cx + 32, head_y + 40)
            path.moveTo(cx + 32, head_y + 40)
            path.lineTo(cx + 25, head_y + 36) # Lash
            painter.drawPath(path)
            # Eyebrow
            painter.setPen(QPen(c_black, 2))
            painter.drawArc(int(cx + 15), int(head_y + 20), 20, 10, 30*16, 120*16)
            
            # Cheeks (Pink Blush)
            painter.setPen(Qt.NoPen)
            painter.setBrush(c_pink)
            painter.drawEllipse(int(cx - 55), int(head_y + 50), 16, 10)
            painter.drawEllipse(int(cx + 39), int(head_y + 50), 16, 10)
            
            # Nose
            painter.setBrush(c_black)
            painter.drawEllipse(int(cx - 6), int(head_y + 58), 12, 8)
            
            # Mouth (Soft Gentle Smile - No Tongue)
            painter.setPen(QPen(c_black, 2))
            painter.setBrush(Qt.NoBrush)
            # Simple curved arc for smile
            painter.drawArc(int(cx - 8), int(head_y + 68), 16, 12, 200 * 16, 140 * 16)

            # Arms
            shoulder_y = head_y + 82
            painter.setBrush(c_grey)
            painter.setPen(Qt.NoPen)
            
            # Right Arm (Waving/Thumbs Up)
            painter.save()
            painter.translate(cx + 38, shoulder_y)
            painter.rotate(-150 * self._arm_angle)
            painter.drawEllipse(QRect(-8, 0, 20, 40))
            painter.restore()
            
            # Left Arm (Down)
            painter.drawEllipse(QRect(int(cx - 52), int(shoulder_y), 20, 40))

        painter.end()


# -----------------------------------------------------------------------------
# REMINDER POPUP
# -----------------------------------------------------------------------------
class ReminderPopupWindow(QWidget):
    def __init__(self, callback_func):
        super().__init__()
        self.callback = callback_func
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(260, 150)
        self.setWindowOpacity(0.0)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10) # Ensure frame is centered in widget
        
        self.frame = QFrame(self)
        self.frame.setObjectName("popup_frame")
        self.layout_f = QVBoxLayout(self.frame)
        self.layout_f.setContentsMargins(20, 20, 20, 20) # Equal padding
        
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0,0,0,80))
        self.shadow.setOffset(0, 5)
        self.frame.setGraphicsEffect(self.shadow)
        
        layout.addWidget(self.frame)
        
        self.lbl = QLabel(REMINDER_MESSAGE)
        self.lbl.setAlignment(Qt.AlignCenter) # Center text
        self.layout_f.addWidget(self.lbl)
        
        self.btn = QPushButton("I drank \U0001F44D")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self.on_click)
        self.layout_f.addWidget(self.btn)
        
        self.setStyleSheet(POPUP_STYLESHEET)
    
    def on_click(self):
        self.btn.setEnabled(False)
        self.callback()
        
    def reset(self):
        self.btn.setEnabled(True)
        self.setWindowOpacity(0.0)

# -----------------------------------------------------------------------------
# MAIN APP CONTROLLER
# -----------------------------------------------------------------------------
class PandaApp(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.bus = StateSignalBus()
        
        self.w_panda = PandaCharacterWindow()
        self.w_popup = ReminderPopupWindow(self.bus.interaction_start.emit)
        
        self.tray = QSystemTrayIcon(self.create_icon())
        menu = QMenu()
        menu.addAction("Disable Reminders", self.toggle)
        menu.addAction("Exit Panda", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.setVisible(True)
        
        self.enabled = True
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_trigger)
        self.timer.start(NORMAL_INTERVAL_MS)
        
        self.setup_connections()

    def create_icon(self):
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setBrush(QColor("white"))
        p.drawEllipse(4, 4, 56, 56)
        p.setBrush(QColor("black"))
        p.drawEllipse(12, 12, 18, 18)
        p.drawEllipse(34, 12, 18, 18)
        p.end()
        return QIcon(pix)

    def setup_connections(self):
        self.bus.start_walk_in.connect(self.seq_walk_in)
        self.bus.arrived_at_center.connect(self.seq_show_popup)
        self.bus.interaction_start.connect(self.seq_thumbs_up)
        self.bus.interaction_done.connect(self.seq_walk_out)
        self.bus.walk_out_finished.connect(self.seq_cleanup)

    def check_trigger(self):
        if self.enabled and not self.w_panda.isVisible():
            self.bus.start_walk_in.emit()

    # --- ANIMATION SEQUENCES -------------------------------------------------

    def seq_walk_in(self):
        (sx, tx, ty), _ = self.get_coords()
        
        # 1. Setup Panda
        self.w_panda.move(int(sx), int(ty))
        self.w_panda.viewAngle = 0.0 # Profile
        self.w_panda.setFacingRight(False) # Walking Left
        self.w_panda.setSmiling(False)
        self.w_panda.armAngle = 0
        self.w_panda.show()
        
        # 2. Parallel Walk (Move X + Oscillate Legs + Bounce Body)
        # Main Move
        self.a_move = QPropertyAnimation(self.w_panda, b"pos")
        self.a_move.setDuration(2000)
        self.a_move.setStartValue(QPoint(int(sx), int(ty)))
        self.a_move.setEndValue(QPoint(int(tx), int(ty)))
        self.a_move.setEasingCurve(QEasingCurve.Linear)
        
        # Legs Scissor (Loop keyframes)
        self.a_legs = QPropertyAnimation(self.w_panda, b"legAngle")
        self.a_legs.setDuration(400) # Fast steps
        self.a_legs.setLoopCount(5) # 5 steps * 400ms = 2000ms
        self.a_legs.setKeyValueAt(0, 0)
        self.a_legs.setKeyValueAt(0.25, 30)
        self.a_legs.setKeyValueAt(0.5, 0)
        self.a_legs.setKeyValueAt(0.75, -30)
        self.a_legs.setKeyValueAt(1, 0)
        
        # Body Bounce (Sync with steps)
        self.a_bounce = QPropertyAnimation(self.w_panda, b"bodyBounce")
        self.a_bounce.setDuration(200) # Half step
        self.a_bounce.setLoopCount(10)
        self.a_bounce.setKeyValueAt(0, 0)
        self.a_bounce.setKeyValueAt(0.5, 4)
        self.a_bounce.setKeyValueAt(1, 0)
        
        self.grp_walk = QParallelAnimationGroup()
        self.grp_walk.addAnimation(self.a_move)
        self.grp_walk.addAnimation(self.a_legs)
        self.grp_walk.addAnimation(self.a_bounce)
        
        self.grp_walk.finished.connect(self.bus.arrived_at_center.emit)
        self.grp_walk.start()

    def seq_show_popup(self):
        # 1. Turn to Front
        self.a_turn = QPropertyAnimation(self.w_panda, b"viewAngle")
        self.a_turn.setDuration(300)
        self.a_turn.setStartValue(0.0)
        self.a_turn.setEndValue(1.0) # Snap to Front
        
        # 2. Show Popup
        _, (px, py) = self.get_coords()
        self.w_popup.move(int(px), int(py))
        self.w_popup.reset()
        self.w_popup.show()
        
        self.a_pop = QPropertyAnimation(self.w_popup, b"windowOpacity")
        self.a_pop.setDuration(500)
        self.a_pop.setStartValue(0.0)
        self.a_pop.setEndValue(1.0)
        
        self.grp_show = QSequentialAnimationGroup()
        self.grp_show.addAnimation(self.a_turn)
        self.grp_show.addAnimation(self.a_pop)
        self.grp_show.start()

    def seq_thumbs_up(self):
        self.w_panda.setSmiling(True)
        self.a_arm = QPropertyAnimation(self.w_panda, b"armAngle")
        self.a_arm.setDuration(400)
        self.a_arm.setStartValue(0.0)
        self.a_arm.setEndValue(1.0)
        self.a_arm.setEasingCurve(QEasingCurve.OutBack)
        
        self.a_arm.finished.connect(self.bus.interaction_done.emit)
        self.a_arm.start()

    def seq_walk_out(self):
        # 1. Hide Pop
        self.a_hide = QPropertyAnimation(self.w_popup, b"windowOpacity")
        self.a_hide.setDuration(300)
        self.a_hide.setStartValue(1.0)
        self.a_hide.setEndValue(0.0)
        
        # 2. Turn Profile (Right)
        self.a_turn_back = QPropertyAnimation(self.w_panda, b"viewAngle")
        self.a_turn_back.setDuration(300)
        self.a_turn_back.setStartValue(1.0)
        self.a_turn_back.setEndValue(0.0)
        
        # 3. Walk Out
        (sx, _, _), _ = self.get_coords()
        cur_pos = self.w_panda.pos()
        
        self.a_out_move = QPropertyAnimation(self.w_panda, b"pos")
        self.a_out_move.setDuration(2000)
        self.a_out_move.setStartValue(cur_pos)
        self.a_out_move.setEndValue(QPoint(int(sx), int(cur_pos.y())))
        self.a_out_move.setEasingCurve(QEasingCurve.Linear)
        
        self.a_out_legs = QPropertyAnimation(self.w_panda, b"legAngle")
        self.a_out_legs.setDuration(400)
        self.a_out_legs.setLoopCount(5)
        self.a_out_legs.setKeyValueAt(0, 0)
        self.a_out_legs.setKeyValueAt(0.25, 30)
        self.a_out_legs.setKeyValueAt(0.5, 0)
        self.a_out_legs.setKeyValueAt(0.75, -30)
        self.a_out_legs.setKeyValueAt(1, 0)
        
        self.a_out_bounce = QPropertyAnimation(self.w_panda, b"bodyBounce")
        self.a_out_bounce.setDuration(200)
        self.a_out_bounce.setLoopCount(10)
        self.a_out_bounce.setKeyValueAt(0, 0)
        self.a_out_bounce.setKeyValueAt(0.5, 4)
        self.a_out_bounce.setKeyValueAt(1, 0)
        
        self.grp_out_walk = QParallelAnimationGroup()
        self.grp_out_walk.addAnimation(self.a_out_move)
        self.grp_out_walk.addAnimation(self.a_out_legs)
        self.grp_out_walk.addAnimation(self.a_out_bounce)
        
        self.seq_all_out = QSequentialAnimationGroup()
        self.seq_all_out.addAnimation(self.a_hide)
        self.seq_all_out.addAnimation(self.a_turn_back)
        self.seq_all_out.addAnimation(self.grp_out_walk)
        
        self.seq_all_out.currentAnimationChanged.connect(self.check_facing_change)
        self.seq_all_out.finished.connect(self.bus.walk_out_finished.emit)
        
        QTimer.singleShot(800, self.seq_all_out.start)

    def check_facing_change(self, current):
        if current == self.grp_out_walk:
            self.w_panda.setFacingRight(True)

    def seq_cleanup(self):
        self.w_panda.hide()
        self.w_popup.hide()

    def get_coords(self):
        screen = QApplication.primaryScreen().availableGeometry()
        pw, ph = 240, 240
        popw, poph = 260, 150
        
        # VISUAL POLISH 2: ALIGNMENT (Fixes "Too Left")
        # Shift panda (tx) much closer to right edge.
        # Original: - pw - 20 // New: - pw + 10
        tx = screen.x() + screen.width() - pw + 10 
        ty = screen.y() + screen.height() - ph - 10
        sx = screen.x() + screen.width() + 50
        
        # popup relative to panda target
        px = tx - popw + 60 # Shifted closer
        py = ty + 60
        return (sx, tx, ty), (px, py)

    def toggle(self): self.enabled = not self.enabled
    def quit(self):
        self.w_panda.close()
        self.w_popup.close()
        self.app.quit()
        
    def run(self): sys.exit(self.app.exec_())

if __name__ == "__main__":
    app = PandaApp()
    app.run()
