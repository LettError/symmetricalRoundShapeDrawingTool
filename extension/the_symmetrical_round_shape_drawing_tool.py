import math
from mojo.events import BaseEventTool, installTool
from mojo.roboFont import CurrentGlyph
from mojo.extensions import ExtensionBundle


bundle = ExtensionBundle("SymmetricalRoundShapeDrawingTool")
toolbarImage = bundle.getResourceImage("toolbar")


class SymmetricalRoundShapeDrawingTool(BaseEventTool):

    BASE_DOT_SIZE = 4

    def setup(self):
        self. minimumWidth = self.minimumHeight = 20
        self.start = None
        self.end = None
        self.xMin = self.yMin = None
        self.xMax = self.yMax = None
        self.lastPt = None
        self._didCalculate = False
        self.flatFactor_x = .25
        self.flatFactor_y = 0
        self.bcpFactor_x = 0.2
        self.bcpFactor_y = 0.2
        self.dragState = None
        self.xComp = self.yComp = 0
        self._orientation = None
        self._shiftDown = False
        self._controlDown = False
        self._circleFactor = 1-0.552284749831

        foregroundContainer = self.extensionContainer(
            identifier="com.letterror.SymmetricalRoundShapeDrawingTool.foreground",
            location="foreground",
            clear=True
        )
        self.dots = foregroundContainer.appendBaseSublayer()
        for ii in range(17):
            self.dots.appendSymbolSublayer(
                position=(0, 0),
                imageSettings=dict(
                    name="oval",
                    size=(self.BASE_DOT_SIZE, self.BASE_DOT_SIZE),
                    fillColor=(0, 0, 0, 0)
                )
            )

        self.captionLayer = foregroundContainer.appendTextLineSublayer(
            size=(400, 100),
            font="Menlo-Regular",
            pointSize=10,
            fillColor=(1, 0.5, 0, 1),
            horizontalAlignment="left"
        )
        self.shapeLayer = foregroundContainer.appendPathSublayer(
            fillColor=(0, 0, 0, 0.03),
            strokeWidth=.5,
            strokeColor=(1, 0, 0, .4),
        )

        previewContainer = self.extensionContainer(
            identifier="com.letterror.SymmetricalRoundShapeDrawingTool.preview",
            location="preview",
            clear=True
        )
        self.previewPathLayer = previewContainer.appendPathSublayer(
            fillColor=(0, 0, 0, 1),
            strokeWidth=2,
            strokeColor=(1, .4, 0, 1),
            strokeDash=(10, 20)
        )
        self.layersVisibility(False)

    def layersVisibility(self, value):
        self.dots.setVisible(value)
        self.captionLayer.setVisible(value)
        self.shapeLayer.setVisible(value)
        self.previewPathLayer.setVisible(value)

    def getToolbarIcon(self):
        return toolbarImage

    def modifiersChanged(self):
        # get modifier keys
        modifiers = self.getModifiers()
        if modifiers.get("shiftDown"):
            self._shiftDown = True
        else:
            self._shiftDown = False
        if modifiers.get("controlDown"):
            self._controlDown = True
        else:
            self._controlDown = False
        if modifiers.get("commandDown"):
            # draggin with command
            self.dragState = "flats"
        elif modifiers.get("optionDown"):
            self.dragState = "curves"
        else:
            self.dragState = "size"

        self.updatePreview()
        self.updateForeground()

    def mouseDown(self, point, clickCount):
        if self.start is None:
            self.start = point.x, point.y

    def mouseDragged(self, point, delta):
        if not self.lastPt:
            self.lastPt = round(point.x), round(point.y)
            return
        self.layersVisibility(True)

        if self._controlDown:
            stepValue = .00025
        else:
            stepValue = .005

        bcpExtrapolateLimit = -.5
        flatExtrapolateLimit = .5

        if self.dragState in [None, 'size']:
            if self.xMin is None:
                self.xMin = round(point.x)
            if self.yMin is None:
                self.yMin = round(point.y)

            if self.xMax is None:
                self.xMax = round(point.x)
            if self.yMax is None:
                self.yMax = round(point.y)
            self.xMax, self.yMax = round(point.x)+self.xComp, round(point.y)+self.yComp
            self.calculate()
            self.lastPt = round(point.x), round(point.y)

        elif self.dragState == "curves":
            dx = self.lastPt[0]-point.x
            dy = self.lastPt[1]-point.y
            self.xComp += dx
            self.yComp += dy
            if dx > 0:
                self.bcpFactor_x += dx * stepValue
                self.bcpFactor_x = max(bcpExtrapolateLimit, min(self.bcpFactor_x, 1))
            else:
                self.bcpFactor_x += dx * stepValue
                self.bcpFactor_x = max(bcpExtrapolateLimit, min(self.bcpFactor_x, 1))
            if dy > 0:
                self.bcpFactor_y -= dy * stepValue
                self.bcpFactor_y = max(bcpExtrapolateLimit, min(self.bcpFactor_y, 1))
            else:
                self.bcpFactor_y -= dy * stepValue
                self.bcpFactor_y = max(bcpExtrapolateLimit, min(self.bcpFactor_y, 1))
            self.lastPt = point.x, point.y

            # snap to significant bcp factor values
            xSnapValues = [self._circleFactor, 0]
            ySnapValues = [self._circleFactor, 0]
            thr = 0.02
            for xSnap in xSnapValues:
                v = max(self.bcpFactor_x, xSnap)-min(self.bcpFactor_x, xSnap)
                if v < thr:
                    self.bcpFactor_x = xSnap
                    break
            for ySnap in ySnapValues:
                v = max(self.bcpFactor_y, ySnap)-min(self.bcpFactor_y, ySnap)
                if v < thr:
                    self.bcpFactor_y = ySnap
                    break
            self.calculate()

        elif self.dragState == "flats":
            dx = self.lastPt[0]-point.x
            dy = self.lastPt[1]-point.y
            self.xComp += dx
            self.yComp += dy
            if dx > 0:
                self.flatFactor_x -= dx * stepValue
                self.flatFactor_x = max(0, min(self.flatFactor_x, 1+flatExtrapolateLimit))
            else:
                self.flatFactor_x -= dx * stepValue
                self.flatFactor_x = max(0, min(self.flatFactor_x, 1+flatExtrapolateLimit))
            if dy > 0:
                self.flatFactor_y += dy * stepValue
                self.flatFactor_y = max(0, min(self.flatFactor_y, 1+flatExtrapolateLimit))
            else:
                self.flatFactor_y += dy * stepValue
                self.flatFactor_y = max(0, min(self.flatFactor_y, 1+flatExtrapolateLimit))
            self.lastPt = point.x, point.y
            self.calculate()

        self.updatePreview()
        self.updateForeground()

    def mouseUp(self, point):
        if self._width is not None and self._height is not None:
            if self._width > self.minimumWidth and self._height > self.minimumHeight:
                self.addShape()
        self.xMin = None
        self.xMax = None
        self.yMin = None
        self.yMax = None
        self._xMin = self._yMin = self._xMax = self._yMax = None
        self._width = self._height = None
        self._didCalculate = False
        self.lastPt = None
        self.xComp = self.yComp = 0

        self.layersVisibility(False)

    def becomeActive(self):
        self.layersVisibility(True)

    def becomeInactive(self):
        self.layersVisibility(False)

    def addShape(self):
        # add the final shape to the glyph
        # try to clean up some of the duplicates
        def notClose(pt1x, pt1y, pt2x, pt2y):
            d = math.hypot(pt1x-pt2x, pt1y-pt2y)
            return d > 5
        g = CurrentGlyph()
        with g.undo("Add RoundShape"):
            p = g.getPen()
            p.moveTo((self._xMin, self._t2_v))
            p.curveTo((self._xMin, self._b2_v), (self._b1_h, self._yMax), (self._t1_h, self._yMax))
            if notClose(self._t1_h, self._yMax, self._t2_h, self._yMax):
                p.lineTo((self._t2_h, self._yMax))
            # do more checking for near-overlaps
            p.curveTo((self._b2_h, self._yMax), (self._xMax, self._b2_v), (self._xMax, self._t2_v))
            if notClose(self._xMax, self._t2_v, self._xMax, self._t1_v):
                p.lineTo((self._xMax, self._t1_v))
            p.curveTo((self._xMax, self._b1_v), (self._b2_h, self._yMin), (self._t2_h, self._yMin))
            if notClose(self._t2_h, self._yMin, self._t1_h, self._yMin):
                p.lineTo((self._t1_h, self._yMin))
            p.curveTo((self._b1_h, self._yMin), (self._xMin, self._b1_v), (self._xMin, self._t1_v))
            p.closePath()

    def updatePreview(self):
        # only draws if there are already outlines in the glyph
        if self._xMin is None:
            return

        self.buildShapePath(self.previewPathLayer.getPen())

    def updateForeground(self):
        if not self._didCalculate:
            return

        bcpDot = tanDot = self.BASE_DOT_SIZE
        if self.dragState == 'flats':
            tanDot = 10
        elif self.dragState == "curves":
            bcpDot = 10

        stackedbv = self._b1_v == self._b2_v
        stackedbh = self._b1_h == self._b2_h
        stackedtv = self._t1_v == self._t2_v
        stackedth = self._t1_h == self._t2_h
        center = .5*(self._xMax+self._xMin), .5*(self._yMax+self._yMin)

        dotsAttributes = [
            ((self._xMin, self._t1_v), tanDot, stackedtv),
            ((self._xMax, self._t1_v), tanDot, stackedtv),
            ((self._xMin, self._t2_v), tanDot, stackedtv),
            ((self._xMax, self._t2_v), tanDot, stackedtv),
            ((self._t1_h, self._yMin), tanDot, stackedth),
            ((self._t1_h, self._yMax), tanDot, stackedth),
            ((self._t2_h, self._yMin), tanDot, stackedth),
            ((self._t2_h, self._yMax), tanDot, stackedth),
            ((self._xMin, self._b1_v), bcpDot, stackedbv),
            ((self._xMax, self._b1_v), bcpDot, stackedbv),
            ((self._xMin, self._b2_v), bcpDot, stackedbv),
            ((self._xMax, self._b2_v), bcpDot, stackedbv),
            ((self._b1_h, self._yMax), bcpDot, stackedbh),
            ((self._b2_h, self._yMax), bcpDot, stackedbh),
            ((self._b1_h, self._yMin), bcpDot, stackedbh),
            ((self._b2_h, self._yMin), bcpDot, stackedbh),
            (center, bcpDot, False),   # center point!
        ]
        dotSublayers = self.dots.getSublayers()
        for index, (pos, size, stacked) in enumerate(dotsAttributes):
            dot = dotSublayers[index]
            with dot.propertyGroup():
                dot.setPosition(pos)
                dot.setImageSettings(
                    dict(name='oval',
                         size=(size, size),
                         fillColor=(0, .5, 1, 1) if stacked else (1, .5, 0, 1))
                )

        self.buildShapePath(self.shapeLayer.getPen())

        captionComponents = [f"the symmetrical,\nround shape\ndrawing tool\npress command to move the flat\npress option to move the bcps\n\nwidth {self._width:3.3f}\nheight {self._height:3.3f}"]
        if self._orientation:
            captionComponents.append("horizontal")
        else:
            captionComponents.append("vertical")
        if self.dragState == "flats":
            captionComponents.append(f"\nyou're changing the flat factor\nx {self.flatFactor_x:3.3f}\ny {self.flatFactor_y:3.3f}")
        elif self.dragState == "curves":
            captionComponents.append(f"\nyou're changing the bcp factor\nx %{self.bcpFactor_x:3.3f}\ny %{self.bcpFactor_y:3.3f}")

        with self.captionLayer.propertyGroup():
            self.captionLayer.setPosition(center)
            self.captionLayer.setText('\n'.join(captionComponents))

    def buildShapePath(self, pen):
        pen.moveTo((self._xMin, self._t2_v))
        pen.curveTo((self._xMin, self._b2_v), (self._b1_h, self._yMax), (self._t1_h, self._yMax))
        pen.lineTo((self._t2_h, self._yMax))
        pen.curveTo((self._b2_h, self._yMax), (self._xMax, self._b2_v), (self._xMax, self._t2_v))
        pen.lineTo((self._xMax, self._t1_v))
        pen.curveTo((self._xMax, self._b1_v), (self._b2_h, self._yMin), (self._t2_h, self._yMin))
        pen.lineTo((self._t1_h, self._yMin))
        pen.curveTo((self._b1_h, self._yMin), (self._xMin, self._b1_v), (self._xMin, self._t1_v))
        pen.closePath()
        return pen

    def calculate(self):
        if self.xMin is None or self.xMax is None or self.yMin is None or self.yMax is None:
            return
        self._didCalculate = True
        self._width = max(self.xMax, self.xMin) - min(self.xMax, self.xMin)
        self._height = max(self.yMax, self.yMin) - min(self.yMax, self.yMin)

        # need different kind of constrain on shift.
        if self._shiftDown:
            self._height = self._width
        # see if we have changed our orientation, flip flats and bcp factors if we did.
        if self._width > self._height:
            isHorizontal = True
        else:
            isHorizontal = False
        if isHorizontal != self._orientation:
            self._orientation = isHorizontal
            self.flatFactor_x, self.flatFactor_y = self.flatFactor_y, self.flatFactor_x
            self.bcpFactor_x, self.bcpFactor_y = self.bcpFactor_y, self.bcpFactor_x

        if self._shiftDown:
            self._xMin = min(self.xMin, self.xMax)
            self._xMax = self._xMin + self._width
            self._yMin = min(self.yMin, self.yMax)
            self._yMax = self._yMin + self._height
        else:
            self._xMin = min(self.xMin, self.xMax)
            self._yMin = min(self.yMin, self.yMax)
            self._xMax = max(self.xMin, self.xMax)
            self._yMax = max(self.yMin, self.yMax)
        # tangent 1, vertical
        self._t1_v = self._yMin+.5*self._height-self.flatFactor_y*.5*self._height
        # tangent 2, vertical
        self._t2_v = self._yMin+.5*self._height+self.flatFactor_y*.5*self._height

        # tangent 1, horizontal
        self._t1_h = self._xMin+.5*self._width-self.flatFactor_x*.5*self._width
        # tangent 2, horizontal
        self._t2_h = self._xMin+.5*self._width+self.flatFactor_x*.5*self._width
        # tangent 1, vertical
        self._t1_v = self._yMin+.5*self._height-self.flatFactor_y*.5*self._height
        # tangent 2, vertical
        self._t2_v = self._yMin+.5*self._height+self.flatFactor_y*.5*self._height
        # tangent 1, horizontal
        self._t1_h = self._xMin+.5*self._width-self.flatFactor_x*.5*self._width
        # tangent 2, horizontal
        self._t2_h = self._xMin+.5*self._width+self.flatFactor_x*.5*self._width

        # bcps
        self._b1_v = self._yMin + self.bcpFactor_y*(self._t1_v-self._yMin)
        self._b2_v = self._t2_v + (1-self.bcpFactor_y)*(self._yMax-self._t2_v)
        self._b1_h = self._xMin + self.bcpFactor_x * (self._t1_h-self._xMin)
        self._b2_h = self._t2_h + (1-self.bcpFactor_x) * (self._xMax-self._t2_h)

    def canSelectWithMarque(self):
        return False

    def getToolbarTip(self):
        return "Symmetrical Round Shape Drawing Tool"


if __name__ == '__main__':
    installTool(SymmetricalRoundShapeDrawingTool())
