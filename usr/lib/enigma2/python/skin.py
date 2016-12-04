from Tools.Profile import profile
profile('LOAD:ElementTree')
import xml.etree.cElementTree
import os
profile('LOAD:enigma_skin')
from enigma import eSize, ePoint, eRect, gFont, eWindow, eLabel, ePixmap, eWindowStyleManager, addFont, gRGB, eWindowStyleSkinned, getDesktop
from Components.config import ConfigSubsection, ConfigText, ConfigSelection, ConfigSlider, config, configfile
from Components.Converter.Converter import Converter
from Components.Sources.Source import Source, ObsoleteSource
from Tools.Directories import resolveFilename, SCOPE_SKIN, SCOPE_FONTS, SCOPE_CURRENT_SKIN, SCOPE_CONFIG, fileExists, SCOPE_SKIN_IMAGE
from Tools.Import import my_import
from Tools.LoadPixmap import LoadPixmap
parameters = dict()
bordersets = dict()
colorNames = dict()
colorNamesInt = dict()
switchPixmap = dict()
cascadingStyleSheets = dict()
piconTypes = dict()
piconTypes['service'] = dict()
piconTypes['provider'] = dict()
piconTypes['satellite'] = dict()
addinfobarTV = [('InfoBarSeparatelyNo', _('no')), ('InfoBarSeparatelyClock', _('separate analog clocks'))]
addinfobarMovie = [('InfoBarSeparatelyMovieNo', _('no')), ('InfoBarSeparatelyMovieClock', _('separate analog clocks'))]
defaultfonts = [('Regular', _('Regular'))]
fonts = {'Body': ('Regular',
          18,
          22,
          16),
 'ChoiceList': ('Regular',
                20,
                24,
                18)}

def queryRestart(configElement):
    config.misc.query_restart.value = True


def dump(x, i = 0):
    print ' ' * i + str(x)
    try:
        for n in x.childNodes:
            dump(n, i + 1)

    except:
        None

    return


class SkinError(Exception):

    def __init__(self, message):
        self.msg = message

    def __str__(self):
        return "[SKIN ERROR] {%s}: %s. Please contact the skin's author!" % (config.skin.primary_skin.value, self.msg)


dom_skins = []

def addSkin(name, scope = SCOPE_SKIN):
    global dom_skins
    filename = resolveFilename(scope, name)
    if fileExists(filename):
        mpath = os.path.dirname(filename) + '/'
        try:
            dom_skins.append((mpath, xml.etree.cElementTree.parse(filename).getroot()))
        except Exception as e:
            print '[SKIN ERROR] error in %s' % filename
            print '[SKIN ERROR] error:', e
            return False

        return True
    return False


config.skin = ConfigSubsection()
config.skin.primary_skin = ConfigText(default='skin.xml')
config.skin.x = ConfigText(default='1280')
config.skin.y = ConfigText(default='720')
config.skin.runningStep = ConfigSlider(default=4, increment=1, limits=(0, 9))
config.skin.osd_font_scale = ConfigSlider(default=35, increment=7, limits=(0, 70))
profile('LoadSkinUser...')
addSkin('skin_user.xml', SCOPE_CONFIG)
profile('LoadSkinBox...')
addSkin('skin_box.xml')
addSkin('skin_subtitles.xml')
profile('LoadSkin...')
if not addSkin(config.skin.primary_skin.value):
    print '[SKIN] defaulting to standard skin...'
    config.skin.primary_skin.value = 'skin.xml'
    addSkin('skin.xml')
profile('LoadSkinDefault...')
addSkin('skin_default.xml')
profile('LoadSkinAllDone')

def parseCoordinate(s, e, size = 0, font = None):
    global fonts
    s = s.strip()
    if s == 'center':
        return (e - size) / 2
    elif s == '*':
        return None
    else:
        if s[0] is 'e':
            val = e
            s = s[1:]
        elif s[0] is 'c':
            val = e / 2
            s = s[1:]
        else:
            val = 0
        if s:
            if s[-1] is '%':
                val += e * int(s[:-1]) / 100
                if val < 0:
                    val = 0
            elif s[-1] is 'w':
                val += fonts[font][3] * int(s[:-1])
                if val < 0:
                    val = 0
            elif s[-1] is 'h':
                val += fonts[font][2] * int(s[:-1])
                if val < 0:
                    val = 0
            else:
                val += int(eval(s))
        return val


def getParentSize(object, desktop):
    size = eSize()
    if object:
        parent = object.getParent()
        if parent and parent.size().isEmpty():
            parent = parent.getParent()
        if parent:
            size = parent.size()
        elif desktop:
            size = desktop.size()
    return size


def parsePosition(s, scale, object = None, desktop = None, size = None):
    x, y = s.split(',')
    parentsize = eSize()
    if object and (x[0] in ('c', 'e') or y[0] in ('c', 'e')):
        parentsize = getParentSize(object, desktop)
    xval = parseCoordinate(x, parentsize.width(), size and size.width())
    yval = parseCoordinate(y, parentsize.height(), size and size.height())
    return ePoint(xval * scale[0][0] / scale[0][1], yval * scale[1][0] / scale[1][1])


def parseSize(s, scale, object = None, desktop = None):
    x, y = s.split(',')
    parentsize = eSize()
    if object and (x[0] in ('c', 'e') or y[0] in ('c', 'e')):
        parentsize = getParentSize(object, desktop)
    xval = parseCoordinate(x, parentsize.width())
    yval = parseCoordinate(y, parentsize.height())
    return eSize(xval * scale[0][0] / scale[0][1], yval * scale[1][0] / scale[1][1])


def parseFont(str, scale):
    list = str.split(';')
    name = list[0]
    size = int(list[1])
    sizemax = None
    if len(list) == 3:
        sizemax = int(list[2])
    if name.find('LCD') == -1 and name.find('VFD') == -1:
        if sizemax and sizemax < size * (65 + config.skin.osd_font_scale.value) / 100:
            size = sizemax * 100 / (65 + config.skin.osd_font_scale.value)
    return gFont(name, int(size) * scale[0][0] / scale[0][1])


def parseColor(s):
    if s[0] != '#':
        try:
            return colorNames[s]
        except:
            raise SkinError("color '%s' must be #aarrggbb or valid named color" % s)

    return gRGB(int(s[1:], 16))


def parseColorInt(s):
    if s[0] != '#':
        try:
            return colorNamesInt[s]
        except:
            raise SkinError("color '%s' must be #aarrggbb or valid named color" % s)

    return int(s[1:], 16)


def getAttribFromCSS(style, name, value):
    for attrib in cascadingStyleSheets[style].keys():
        _value = cascadingStyleSheets[style][attrib]
        if attrib == name:
            return _value
        if attrib == 'css':
            value = getAttribFromCSS(_value, name, value)
            if value:
                return value

    return value


def getAttribScreen(attrib, name):
    value = attrib.get(name)
    if value:
        return value
    styles = attrib.get('css')
    if styles:
        styles = styles.split(',')
        for style in styles:
            style = style.strip()
            value = getAttribFromCSS(style, name, value)
            if value:
                return value

    return value


def collectAttributes(skinAttributes, node, context, skin_path_prefix = None, ignore = (), filenames = frozenset(('pixmap',
 'pointer',
 'seek_pointer',
 'backgroundPixmap',
 'selectionPixmap',
 'sstartPixmap',
 'sbodyPixmap',
 'sendPixmap',
 'sballPixmap',
 'sbackgroundPixmap',
 'sliderBackground',
 'sliderForeground',
 'sliderPointer',
 'tipTop',
 'tipBottom',
 'tipLeft',
 'tipReight'))):
    size = None
    pos = None
    font = None
    for attrib, value in node.items():
        if attrib not in ignore:
            if attrib in filenames:
                value = resolveFilename(SCOPE_CURRENT_SKIN, value, path_prefix=skin_path_prefix)
            if attrib == 'size':
                size = value
            elif attrib == 'position':
                pos = value
            elif attrib == 'font':
                font = value
            else:
                skinAttributes.append((attrib, value.encode('utf-8')))

    if font is None:
        font = getAttribScreen(node.attrib, 'font')
    if size is None:
        size = getAttribScreen(node.attrib, 'size')
    if pos is None:
        pos = getAttribScreen(node.attrib, 'position')
    if font is not None:
        font = font.encode('utf-8')
        skinAttributes.append(('font', font))
    if size is not None:
        size = size.encode('utf-8')
    if pos is not None:
        pos = pos.encode('utf-8')
        pos, size = context.parse(pos, size, font)
        skinAttributes.append(('position', pos))
    if size is not None:
        skinAttributes.append(('size', size))
    return


def loadPixmap(path, desktop):
    cached = False
    option = path.find('#')
    if option != -1:
        options = path[option + 1:].split(',')
        path = path[:option]
        cached = 'cached' in options
    ptr = LoadPixmap(path, desktop, cached)
    if ptr is None:
        raise SkinError('pixmap file %s not found!' % path)
    return ptr


class AttributeParser():

    def __init__(self, guiObject, desktop, scale = ((1, 1), (1, 1))):
        self.guiObject = guiObject
        self.desktop = desktop
        self.scaleTuple = scale

    def applyOne(self, attrib, value):
        try:
            getattr(self, attrib.lower())(value)
        except AttributeError:
            print '[SKIN] Attribute not implemented:', attrib, 'value:', value
        except SkinError as ex:
            print '[SKIN ERROR]', ex

    def applyAll(self, attrs):
        firstattrs = []
        secondattrs = []
        for attrib, value in attrs:
            if attrib.lower() == 'font':
                secondattrs.append((0, attrib, value))
            if attrib.lower() == 'size':
                secondattrs.append((1, attrib, value))
            elif attrib.lower() == 'position':
                secondattrs.append((2, attrib, value))
            elif attrib.lower() == 'itemheight':
                secondattrs.append((3, attrib, value))
            elif attrib.lower() == 'itemwidth':
                secondattrs.append((4, attrib, value))
            elif attrib.lower() == 'cursorsize':
                secondattrs.append((5, attrib, value))
            elif attrib.lower() == 'orientation':
                secondattrs.append((6, attrib, value))
            elif attrib.lower() == 'runningstep':
                secondattrs.append((7, attrib, value))
            else:
                firstattrs.append((attrib, value))

        if len(secondattrs) > 0:
            secondattrs.sort(key=lambda x: x[0])
            attrs = firstattrs + [ (attrib, value) for x, attrib, value in secondattrs ]
        for attrib, value in attrs:
            self.applyOne(attrib, value)

    def conditional(self, value):
        pass

    def position(self, value):
        self.guiObject.move(parsePosition(value, self.scaleTuple, self.desktop, self.guiObject.csize()))

    def size(self, value):
        self.guiObject.resize(parseSize(value, self.scaleTuple))

    def textframeoffset(self, value):
        self.guiObject.setTextFrameOffset(parsePosition(value, self.scaleTuple))

    def textframesize(self, value):
        self.guiObject.setTextFrameSize(parseSize(value, self.scaleTuple))

    def frameoffset(self, value):
        self.guiObject.setFrameOffset(parsePosition(value, self.scaleTuple))

    def framesize(self, value):
        self.guiObject.setFrameSize(parseSize(value, self.scaleTuple))

    def title(self, value):
        self.guiObject.setTitle(_(value))

    def text(self, value):
        self.guiObject.setText(_(value))

    def font(self, value):
        self.guiObject.setFont(parseFont(value, self.scaleTuple))

    def zposition(self, value):
        self.guiObject.setZPosition(int(value))

    def itemheight(self, value):
        self.guiObject.setItemHeight(int(value))

    def itemwidth(self, value):
        self.guiObject.setItemWidth(int(value))

    def cursoroffset(self, value):
        self.guiObject.setCursorOffsetCustom(parsePosition(value, self.scaleTuple))

    def cursorsize(self, value):
        self.guiObject.setCursorSizeCustom(parseSize(value, self.scaleTuple))

    def scrollbarwidth(self, value):
        self.guiObject.setScrollBarWidth(int(value))

    def scrollbarheight(self, value):
        self.guiObject.setScrollBarHeight(int(value))

    def pixmap(self, value):
        self.guiObject.setPixmap(loadPixmap(value, self.desktop))

    def backgroundpixmap(self, value):
        self.guiObject.setBackgroundPicture(loadPixmap(value, self.desktop))

    def selectionpixmap(self, value):
        self.guiObject.setSelectionPicture(loadPixmap(value, self.desktop))

    def sliderbackground(self, value):
        self.guiObject.setPixmap(loadPixmap(value, self.desktop), self.guiObject.SliderBackground)

    def sliderforeground(self, value):
        self.guiObject.setPixmap(loadPixmap(value, self.desktop), self.guiObject.SliderForeground)

    def sliderpointer(self, value):
        self.guiObject.setPixmap(loadPixmap(value, self.desktop), self.guiObject.SliderPointer)

    def tiptop(self, value):
        self.guiObject.setPixmap(loadPixmap(value, self.desktop), self.guiObject.TipTop)

    def tipbottom(self, value):
        self.guiObject.setPixmap(loadPixmap(value, self.desktop), self.guiObject.TipBottom)

    def tipleft(self, value):
        self.guiObject.setPixmap(loadPixmap(value, self.desktop), self.guiObject.TipLeft)

    def tipreight(self, value):
        self.guiObject.setPixmap(loadPixmap(value, self.desktop), self.guiObject.TipReight)

    def alphatest(self, value):
        self.guiObject.setAlphatest({'on': 1,
         'off': 0,
         'blend': 2}[value.lower()])

    def scale(self, value):
        self.guiObject.setScale(1)

    def orientation(self, value):
        try:
            self.guiObject.setOrientation(*{'orvertical': (self.guiObject.orVertical, False),
             'ortoptobottom': (self.guiObject.orVertical, False),
             'orbottomtotop': (self.guiObject.orVertical, True),
             'orhorizontal': (self.guiObject.orHorizontal, False),
             'orlefttoright': (self.guiObject.orHorizontal, False),
             'orrighttoleft': (self.guiObject.orHorizontal, True)}[value.lower()])
        except KeyError:
            print '[SKIN ERROR] oprientation must be either orVertical or orHorizontal!'

    def valign(self, value):
        try:
            self.guiObject.setVAlign({'top': self.guiObject.alignTop,
             'center': self.guiObject.alignCenter,
             'bottom': self.guiObject.alignBottom}[value.lower()])
        except KeyError:
            print '[SKIN ERROR] valign must be either top, center or bottom!'

    def halign(self, value):
        try:
            self.guiObject.setHAlign({'left': self.guiObject.alignLeft,
             'center': self.guiObject.alignCenter,
             'right': self.guiObject.alignRight,
             'block': self.guiObject.alignBlock}[value.lower()])
        except KeyError:
            print '[SKIN ERROR] halign must be either left, center, right or block!'

    def align(self, value):
        self.valign(value)
        self.halign(value)

    def flags(self, value):
        flags = value.split(',')
        for f in flags:
            try:
                fv = eWindow.__dict__[f]
                self.guiObject.setFlag(fv)
            except KeyError:
                print '[SKIN ERROR] illegal flag %s!' % f

    def backgroundcolor(self, value):
        self.guiObject.setBackgroundColor(parseColor(value))

    def backgroundcolorselected(self, value):
        self.guiObject.setBackgroundColorSelected(parseColor(value))

    def foregroundcolor(self, value):
        self.guiObject.setForegroundColor(parseColor(value))

    def foregroundcolorselected(self, value):
        self.guiObject.setForegroundColorSelected(parseColor(value))

    def shadowcolor(self, value):
        self.guiObject.setShadowColor(parseColor(value))

    def selectiondisabled(self, value):
        self.guiObject.setSelectionEnable(0)

    def transparent(self, value):
        self.guiObject.setTransparent(int(value))

    def bordercolor(self, value):
        self.guiObject.setBorderColor(parseColor(value))

    def borderwidth(self, value):
        self.guiObject.setBorderWidth(int(value))

    def shifttext(self, value):
        self.guiObject.setShift(int(value))

    def scrollbarmode(self, value):
        self.guiObject.setScrollbarMode({'showondemand': self.guiObject.showOnDemand,
         'showalways': self.guiObject.showAlways,
         'shownever': self.guiObject.showNever,
         'showtip': self.guiObject.showTip}[value.lower()])

    def enablewraparound(self, value):
        self.guiObject.setWrapAround(True)

    def enablewraparoundvertical(self, value):
        self.guiObject.setWrapAroundVertical(True)

    def enablewraparoundhorizontal(self, value):
        self.guiObject.setWrapAroundHorizontal(True)

    def enablelinebreaks(self, value):
        self.guiObject.setLineBreaks(True)

    def pointer(self, value):
        name, pos = value.split(':')
        pos = parsePosition(pos, self.scaleTuple)
        ptr = loadPixmap(name, self.desktop)
        self.guiObject.setPointer(0, ptr, pos)

    def seek_pointer(self, value):
        name, pos = value.split(':')
        pos = parsePosition(pos, self.scaleTuple)
        ptr = loadPixmap(name, self.desktop)
        self.guiObject.setPointer(1, ptr, pos)

    def shadowoffset(self, value):
        self.guiObject.setShadowOffset(parsePosition(value, self.scaleTuple))

    def css(self, value):
        styles = value.split(',')
        for style in styles:
            style = style.strip()
            for _attrib in cascadingStyleSheets[style].keys():
                _value = cascadingStyleSheets[style][_attrib]
                self.applyOne(_attrib, _value)

    def sliderlength(self, value):
        pass

    def sliderlengthtip(self, value):
        self.guiObject.setLengthTip(int(value))

    def nowrap(self, value):
        self.guiObject.setNoWrap(1)

    def runningline(self, value):
        self.guiObject.setRunningLine(int(value))

    def runninglist(self, value):
        self.guiObject.setRunningList(int(value))

    def runningcursor(self, value):
        self.guiObject.setRunningCursor(int(value))

    def runningstep(self, value):
        if value[0].lower() == 'x':
            if self.guiObject.getOrientation() == self.guiObject.orHorizontal:
                autoval = self.guiObject.getItemWidth() / (1 + config.skin.runningStep.value)
                print '[SKIN] set runningstep: %s->%d H(%dx%d)' % (value,
                 autoval,
                 self.guiObject.getItemWidth(),
                 self.guiObject.getItemHeight())
            else:
                autoval = self.guiObject.getItemHeight() / (1 + config.skin.runningStep.value)
                print '[SKIN] set runningstep: %s->%d V(%dx%d)' % (value,
                 autoval,
                 self.guiObject.getItemWidth(),
                 self.guiObject.getItemHeight())
            value = autoval if autoval != 0 else value[1:]
        self.guiObject.setRunningStep(int(value))

    def enablemultilist(self, value):
        self.guiObject.setMultiList(True)

    def id(self, value):
        pass


def applySingleAttribute(guiObject, desktop, attrib, value, scale = ((1, 1), (1, 1))):
    AttributeParser(guiObject, desktop, scale).applyOne(attrib, value)


def applyAllAttributes(guiObject, desktop, attributes, scale):
    AttributeParser(guiObject, desktop, scale).applyAll(attributes)


def loadSingleSkinData(desktop, skin, path_prefix):
    global bordersets
    for c in skin.findall('output'):
        sid = c.attrib.get('id')
        if sid:
            sid = int(sid)
        else:
            sid = 0
        if sid == 0:
            for res in c.findall('resolution'):
                get_attr = res.attrib.get
                xres = int(get_attr('xres', 1280))
                yres = int(get_attr('yres', 720))
                bpp = int(get_attr('bpp', 32))
                config.skin.x.value = str(xres)
                config.skin.y.value = str(yres)
                config.skin.save()
                from enigma import gMainDC
                gMainDC.getInstance().setResolution(xres, yres)
                desktop.resize(eSize(xres, yres))

    for skininclude in skin.findall('include'):
        filename = skininclude.attrib.get('filename')
        if filename:
            skinfile = resolveFilename(SCOPE_CURRENT_SKIN, filename, path_prefix=path_prefix)
            if not fileExists(skinfile):
                skinfile = resolveFilename(SCOPE_SKIN_IMAGE, filename, path_prefix=path_prefix)
            if fileExists(skinfile):
                print '[SKIN] loading include:', skinfile
                loadSkin(skinfile)

    for c in skin.findall('picons'):
        picon_type = c.attrib.get('type')
        for picon in c.findall('picon'):
            get_attr = picon.attrib.get
            picon_id = get_attr('id')
            folder = get_attr('folder')
            size = parseSize(get_attr('size'), scale=((1, 1), (1, 1)))
            width = size.width()
            height = size.height()
            mirror = int(get_attr('mirror', 0))
            offset = int(get_attr('offset', 0))
            transparent = int(get_attr('transparent', 0))
            pixmap = get_attr('pixmap', 'no')
            piconTypes[picon_type][picon_id] = [folder,
             width,
             height,
             mirror,
             offset,
             transparent,
             pixmap]

    from Components.SystemInfo import SystemInfo
    if SystemInfo['Weather'] and len(addinfobarTV) == 2:
        addinfobarTV.append(('InfoBarSeparatelyWeatherCurrent', _('current weather')))
        addinfobarTV.append(('InfoBarSeparatelyWeather3days', _('weather for three days')))
        addinfobarTV.append(('InfoBarSeparatelyWeatherCurrentAndClock', _('current weather & clock')))
        addinfobarTV.append(('InfoBarSeparatelyWeather3daysAndClock', _('weather for three days & clock')))
    if SystemInfo['Weather'] and len(addinfobarMovie) == 2:
        addinfobarMovie.append(('InfoBarSeparatelyMovieWeatherCurrent', _('current weather')))
        addinfobarMovie.append(('InfoBarSeparatelyMovieWeather3days', _('weather for three days')))
        addinfobarMovie.append(('InfoBarSeparatelyMovieWeatherCurrentAndClock', _('current weather & clock')))
        addinfobarMovie.append(('InfoBarSeparatelyMovieWeather3daysAndClock', _('weather for three days & clock')))
    for c in skin.findall('addinfobar'):
        addinfobar_type = c.attrib.get('type')
        for addinfobar in c.findall('screen'):
            get_attr = addinfobar.attrib.get
            addinfobar_name = get_attr('name')
            addinfobar_text = get_attr('text')
            if addinfobar_type == 'TV':
                addinfobarTV.append((addinfobar_name, addinfobar_text))
            else:
                addinfobarMovie.append((addinfobar_name, addinfobar_text))

    config.usage.added_infobar_mode = ConfigSelection(default='InfoBarSeparatelyNo', choices=addinfobarTV)
    config.usage.added_infobar_mode.addNotifier(queryRestart, initial_call=False)
    config.usage.added_infobar_mode_movie = ConfigSelection(default='InfoBarSeparatelyMovieNo', choices=addinfobarMovie)
    config.usage.added_infobar_mode_movie.addNotifier(queryRestart, initial_call=False)
    for c in skin.findall('colors'):
        for color in c.findall('color'):
            get_attr = color.attrib.get
            name = get_attr('name')
            color = get_attr('value')
            if name and color:
                colorNames[name] = parseColor(color)
                colorNamesInt[name] = parseColorInt(color)
            else:
                print SkinError('need color and name, got %s %s' % (name, color))

    for c in skin.findall('switchpixmap'):
        for pixmap in c.findall('pixmap'):
            get_attr = pixmap.attrib.get
            name = get_attr('name')
            filename = get_attr('filename')
            if name and filename:
                resolved_png = resolveFilename(SCOPE_CURRENT_SKIN, filename, path_prefix=path_prefix)
                if fileExists(resolved_png):
                    switchPixmap[name] = resolved_png
                else:
                    raise SkinError('need filename, got', filename)
            else:
                print SkinError('need filename and name, got %s %s' % (name, filename))

    for c in skin.findall('cascadingstylesheets'):
        stylename = c.attrib.get('name')
        cascadingStyleSheets[stylename] = dict()
        for pixmap in c.findall('css'):
            get_attr = pixmap.attrib.get
            name = get_attr('name')
            value = get_attr('value')
            if name in ('pixmap', 'pointer', 'seek_pointer', 'backgroundPixmap', 'selectionPixmap', 'sstartPixmap', 'sbodyPixmap', 'sendPixmap', 'sballPixmap', 'sbackgroundPixmap', 'sliderBackground', 'sliderForeground', 'sliderPointer', 'tipTop', 'tipBottom', 'tipLeft', 'tipReight'):
                value = resolveFilename(SCOPE_CURRENT_SKIN, value, path_prefix=path_prefix)
            cascadingStyleSheets[stylename][name] = value.encode('utf-8')

    for c in skin.findall('defaultfonts'):
        for font in c.findall('font'):
            get_attr = font.attrib.get
            name = get_attr('name', 'Regular')
            text = get_attr('text', 'Regular')
            if name != 'Regular':
                defaultfonts.append((name, _(text)))

    config.skin.osd_font_default = ConfigSelection(choices=defaultfonts, default='Regular')
    config.skin.osd_font_scale.addNotifier(queryRestart, initial_call=False)
    config.skin.osd_font_default.addNotifier(queryRestart, initial_call=False)
    for c in skin.findall('fonts'):
        added_font = []
        regular_font = None
        for font in c.findall('font'):
            get_attr = font.attrib.get
            filename = get_attr('filename', '<NONAME>')
            name = get_attr('name', 'Regular')
            scale = get_attr('scale')
            if scale:
                scale = int(scale)
            else:
                scale = 100
            if name.find('LCD') == -1 and name.find('VFD') == -1:
                scale = scale * (65 + config.skin.osd_font_scale.value) / 100
            else:
                scale = scale
            is_replacement = get_attr('replacement') and True or False
            render = get_attr('render')
            if render:
                render = int(render)
            else:
                render = 0
            resolved_font = resolveFilename(SCOPE_FONTS, filename, path_prefix=path_prefix)
            if not fileExists(resolved_font):
                skin_path = resolveFilename(SCOPE_CURRENT_SKIN, filename)
                if fileExists(skin_path):
                    resolved_font = skin_path
            if name == config.skin.osd_font_default.value:
                addFont(resolved_font, 'Regular', scale, is_replacement, render)
                added_font.append('Regular')
            if name == 'Regular':
                regular_font = (resolved_font,
                 name,
                 scale,
                 is_replacement,
                 render)
            else:
                addFont(resolved_font, name, scale, is_replacement, render)
                added_font.append(name)

        if 'Regular' not in added_font and regular_font is not None:
            resolved_font, name, scale, is_replacement, render = regular_font
            addFont(resolved_font, name, scale, is_replacement, render)
        for alias in c.findall('alias'):
            get = alias.attrib.get
            try:
                name = get('name')
                font = get('font')
                size = int(get('size'))
                height = int(get('height', size))
                width = int(get('width', size))
                fonts[name] = (font,
                 size,
                 height,
                 width)
            except Exception as ex:
                print '[SKIN ERROR] bad font alias', ex

    for c in skin.findall('parameters'):
        for parameter in c.findall('parameter'):
            get = parameter.attrib.get
            try:
                name = get('name')
                value = get('value')
                parameters[name] = map(int, value.split(','))
            except Exception as ex:
                print '[SKIN ERROR] bad parameter', ex

    for c in skin.findall('subtitles'):
        from enigma import eWidget, eSubtitleWidget
        scale = ((1, 1), (1, 1))
        for substyle in c.findall('sub'):
            get_attr = substyle.attrib.get
            font = parseFont(get_attr('font'), scale)
            col = get_attr('foregroundColor')
            if col:
                foregroundColor = parseColor(col)
                haveColor = 1
            else:
                foregroundColor = gRGB(16777215)
                haveColor = 0
            col = get_attr('borderColor')
            if col:
                borderColor = parseColor(col)
            else:
                borderColor = gRGB(0)
            borderwidth = get_attr('borderWidth')
            if borderwidth is None:
                borderWidth = 3
            else:
                borderWidth = int(borderwidth)
            face = eSubtitleWidget.__dict__[get_attr('name')]
            eSubtitleWidget.setFontStyle(face, font, haveColor, foregroundColor, borderColor, borderWidth)

    for windowstyle in skin.findall('windowstyle'):
        style = eWindowStyleSkinned()
        style_id = windowstyle.attrib.get('id')
        if style_id:
            style_id = int(style_id)
        else:
            style_id = 0
        font = gFont('Regular', 20)
        offset = eSize(20, 5)
        for title in windowstyle.findall('title'):
            get_attr = title.attrib.get
            offset = parseSize(get_attr('offset'), ((1, 1), (1, 1)))
            font = parseFont(get_attr('font'), ((1, 1), (1, 1)))

        style.setTitleFont(font)
        style.setTitleOffset(offset)
        for borderset in windowstyle.findall('borderset'):
            bsName = str(borderset.attrib.get('name'))
            bsMargin = borderset.attrib.get('margin')
            if bsMargin:
                top, bottom, left, right = bsMargin.split(',')
                bordersets[bsName] = [int(top),
                 int(bottom),
                 int(left),
                 int(right)]
            for pixmap in borderset.findall('pixmap'):
                get_attr = pixmap.attrib.get
                bpName = get_attr('pos')
                filename = get_attr('filename')
                if filename and bpName:
                    png = loadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, filename, path_prefix=path_prefix), desktop)
                    style.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], png)

        for borderset in windowstyle.findall('sliderset'):
            bsName = str(borderset.attrib.get('name'))
            bpTip = borderset.attrib.get('tip')
            if bpTip:
                style.setSliderTip(eWindowStyleSkinned.__dict__[bsName], int(bpTip))
            for pixmap in borderset.findall('pixmap'):
                get_attr = pixmap.attrib.get
                bpName = get_attr('pos')
                filename = get_attr('filename')
                if filename and bpName:
                    png = loadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, filename, path_prefix=path_prefix), desktop)
                    style.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], png)

        for color in windowstyle.findall('color'):
            get_attr = color.attrib.get
            colorType = get_attr('name')
            color = parseColor(get_attr('color'))
            try:
                style.setColor(eWindowStyleSkinned.__dict__['col' + colorType], color)
            except:
                raise SkinError('Unknown color %s' % colorType)

        x = eWindowStyleManager.getInstance()
        x.setStyle(style_id, style)

    for margin in skin.findall('margin'):
        style_id = margin.attrib.get('id')
        if style_id:
            style_id = int(style_id)
        else:
            style_id = 0
        r = eRect(0, 0, 0, 0)
        v = margin.attrib.get('left')
        if v:
            r.setLeft(int(v))
        v = margin.attrib.get('top')
        if v:
            r.setTop(int(v))
        v = margin.attrib.get('right')
        if v:
            r.setRight(int(v))
        v = margin.attrib.get('bottom')
        if v:
            r.setBottom(int(v))
        getDesktop(style_id).setMargins(r)

    return


dom_screens = {}

def loadSkin(name, scope = SCOPE_SKIN):
    global dom_screens
    filename = resolveFilename(scope, name)
    if fileExists(filename):
        path = os.path.dirname(filename) + '/'
        for elem in xml.etree.cElementTree.parse(filename).getroot():
            if elem.tag == 'screen':
                name = elem.attrib.get('name', None)
                if name:
                    if name in dom_screens:
                        elem.clear()
                    else:
                        dom_screens[name] = (elem, path)
                else:
                    elem.clear()
            else:
                elem.clear()

    return


def loadSkinData(desktop):
    global dom_skins
    skins = dom_skins[:]
    skins.reverse()
    for path, dom_skin in skins:
        loadSingleSkinData(desktop, dom_skin, path)
        for elem in dom_skin:
            if elem.tag == 'screen':
                name = elem.attrib.get('name', None)
                if name:
                    if name in dom_screens:
                        dom_screens[name][0].clear()
                    dom_screens[name] = (elem, path)
                else:
                    elem.clear()
            else:
                elem.clear()

    del dom_skins
    return


class additionalWidget():
    pass


class SizeTuple(tuple):

    def split(self, *args):
        return (str(self[0]), str(self[1]))

    def strip(self, *args):
        return '%s,%s' % self

    def __str__(self):
        return '%s,%s' % self


class SkinContext():

    def __init__(self, parent = None, pos = None, size = None, font = None, bottom = 0, top = 0, left = 0, right = 0):
        if parent is not None:
            if pos is not None:
                pos, size = parent.parse(pos, size, font)
                self.x, self.y = pos
                self.w, self.h = size
                self.x += left
                self.y += top
                self.w -= left + right
                self.h -= top + bottom
            else:
                self.x = None
                self.y = None
                self.w = None
                self.h = None
        return

    def __str__(self):
        return 'Context (%s,%s)+(%s,%s) ' % (self.x,
         self.y,
         self.w,
         self.h)

    def parse(self, pos, size, font):
        if pos == 'fill':
            pos = (self.x, self.y)
            size = (self.w, self.h)
            self.w = 0
            self.h = 0
        else:
            w, h = size.split(',')
            w = parseCoordinate(w, self.w, 0, font)
            h = parseCoordinate(h, self.h, 0, font)
            if pos == 'bottom':
                pos = (self.x, self.y + self.h - h)
                size = (self.w, h)
                self.h -= h
            elif pos == 'top':
                pos = (self.x, self.y)
                size = (self.w, h)
                self.h -= h
                self.y += h
            elif pos == 'left':
                pos = (self.x, self.y)
                size = (w, self.h)
                self.x += w
                self.w -= w
            elif pos == 'right':
                pos = (self.x + self.w - w, self.y)
                size = (w, self.h)
                self.w -= w
            else:
                size = (w, h)
                pos = pos.split(',')
                pos = (self.x + parseCoordinate(pos[0], self.w, size[0], font), self.y + parseCoordinate(pos[1], self.h, size[1], font))
        return (SizeTuple(pos), SizeTuple(size))


class SkinContextStack(SkinContext):

    def parse(self, pos, size, font):
        if pos == 'fill':
            pos = (self.x, self.y)
            size = (self.w, self.h)
        else:
            w, h = size.split(',')
            w = parseCoordinate(w, self.w, 0, font)
            h = parseCoordinate(h, self.h, 0, font)
            if pos == 'bottom':
                pos = (self.x, self.y + self.h - h)
                size = (self.w, h)
            elif pos == 'top':
                pos = (self.x, self.y)
                size = (self.w, h)
            elif pos == 'left':
                pos = (self.x, self.y)
                size = (w, self.h)
            elif pos == 'right':
                pos = (self.x + self.w - w, self.y)
                size = (w, self.h)
            else:
                size = (w, h)
                pos = pos.split(',')
                pos = (self.x + parseCoordinate(pos[0], self.w, size[0], font), self.y + parseCoordinate(pos[1], self.h, size[1], font))
        return (SizeTuple(pos), SizeTuple(size))


def readSkin(screen, skin, names, desktop):
    if not isinstance(names, list):
        names = [names]
    for n in names:
        myscreen, path = dom_screens.get(n, (None, None))
        if myscreen is not None:
            name = n
            break
    else:
        name = "<embedded-in-'%s'>" % screen.__class__.__name__

    if myscreen is None:
        myscreen = getattr(screen, 'parsedSkin', None)
    if myscreen is None and getattr(screen, 'skin', None):
        skin = screen.skin
        display_skin_id = desktop.getStyleID()
        print '[SKIN] Parsing embedded skin %s for dislay skin id %d' % (name, display_skin_id)
        if isinstance(skin, tuple):
            for s in skin:
                candidate = xml.etree.cElementTree.fromstring(s)
                if candidate.tag == 'screen':
                    sid = candidate.attrib.get('id', None)
                    if not sid or int(sid) == display_skin_id:
                        myscreen = candidate
                        break
            else:
                print '[SKIN] Hey, no suitable screen!'

        else:
            myscreen = xml.etree.cElementTree.fromstring(skin)
        if myscreen:
            screen.parsedSkin = myscreen
    if myscreen is None:
        print '[SKIN] No skin to read...'
        myscreen = screen.parsedSkin = xml.etree.cElementTree.fromstring('<screen></screen>')
    screen.skinAttributes = []
    skin_path_prefix = getattr(screen, 'skin_path', path)
    context = SkinContextStack()
    s = desktop.bounds()
    context.x = s.left()
    context.y = s.top()
    context.w = s.width()
    context.h = s.height()
    del s
    collectAttributes(screen.skinAttributes, myscreen, context, skin_path_prefix, ignore=('name',))
    top = bottom = left = right = 0
    flags = getAttribScreen(myscreen.attrib, 'flags')
    if flags:
        for flag in flags.split(','):
            if flag == 'wfTitle':
                top, bottom, left, right = bordersets['bsWindow']
                break
            elif flag == 'wfNoTitle':
                top, bottom, left, right = bordersets['bsWindowNoTitle']
                break

    context = SkinContext(context, getAttribScreen(myscreen.attrib, 'position'), getAttribScreen(myscreen.attrib, 'size'), bottom=bottom, top=top, left=left, right=right)
    screen.additionalWidgets = []
    screen.renderer = []
    visited_components = set()

    def process_none(widget, context):
        pass

    def process_widget(widget, context):
        get_attr = widget.attrib.get
        wname = get_attr('name')
        wsource = get_attr('source')
        if wname is None and wsource is None:
            print '[SKIN] widget has no name and no source!'
            return
        else:
            if wname and wsource is None:
                visited_components.add(wname)
                try:
                    attributes = screen[wname].skinAttributes = []
                except:
                    raise SkinError("component with name '" + wname + "' was not found in skin of screen '" + name + "'!")

                collectAttributes(attributes, widget, context, skin_path_prefix, ignore=('name',))
            elif wsource:
                while True:
                    scr = screen
                    path = wsource.split('.')
                    while len(path) > 1:
                        scr = screen.getRelatedScreen(path[0])
                        if scr is None:
                            raise SkinError("specified related screen '" + wsource + "' was not found in screen '" + name + "'!")
                        path = path[1:]

                    source = scr.get(path[0])
                    if isinstance(source, ObsoleteSource):
                        print "WARNING: SKIN '%s' USES OBSOLETE SOURCE '%s', USE '%s' INSTEAD!" % (name, wsource, source.new_source)
                        print 'OBSOLETE SOURCE WILL BE REMOVED %s, PLEASE UPDATE!' % source.removal_date
                        if source.description:
                            print source.description
                        wsource = source.new_source
                    else:
                        break

                if source is None:
                    raise SkinError("source '" + wsource + "' was not found in screen '" + name + "'!")
                wrender = get_attr('render')
                if not wrender:
                    raise SkinError("you must define a renderer with render= for source '%s'" % wsource)
                sub_source_list = []
                for converter in widget.findall('convert'):
                    ctype = converter.get('type')
                    try:
                        parms = converter.text.strip()
                    except:
                        parms = ''

                    converter_class = my_import('.'.join(('Components', 'Converter', ctype))).__dict__.get(ctype)
                    sub_source = converter.get('source')
                    if sub_source is None:
                        c = None
                        for i in source.downstream_elements:
                            if isinstance(i, converter_class) and i.converter_arguments == parms:
                                c = i

                        if c is None:
                            c = converter_class(parms)
                            if len(sub_source_list) == 0:
                                c.connect(source)
                            else:
                                for source in sub_source_list:
                                    c.connect(source)

                                sub_source_list = []
                        source = c
                    else:
                        wsource = sub_source
                        while True:
                            scr = screen
                            path = wsource.split('.')
                            while len(path) > 1:
                                scr = screen.getRelatedScreen(path[0])
                                if scr is None:
                                    raise SkinError("specified related screen '" + wsource + "' was not found in screen '" + name + "'!")
                                path = path[1:]

                            ssource = scr.get(path[0])
                            if isinstance(ssource, ObsoleteSource):
                                print "WARNING: SKIN '%s' USES OBSOLETE SOURCE '%s', USE '%s' INSTEAD!" % (name, wsource, ssource.new_source)
                                print 'OBSOLETE SOURCE WILL BE REMOVED %s, PLEASE UPDATE!' % ssource.removal_date
                                if ssource.description:
                                    print ssource.description
                                wsource = ssource.new_source
                            else:
                                break

                        c = None
                        for i in ssource.downstream_elements:
                            if isinstance(i, converter_class) and i.converter_arguments == parms:
                                c = i

                        if c is None:
                            c = converter_class(parms)
                            c.connect(ssource)
                        sub_source_list.append(c)

                renderer_class = my_import('.'.join(('Components', 'Renderer', wrender))).__dict__.get(wrender)
                renderer = renderer_class()
                renderer.connect(source)
                renderer.name = wname
                attributes = renderer.skinAttributes = []
                collectAttributes(attributes, widget, context, skin_path_prefix, ignore=('render', 'source', 'name'))
                screen.renderer.append(renderer)
            return

    def process_applet(widget, context):
        try:
            codeText = widget.text.strip()
            widgetType = widget.attrib.get('type')
            code = compile(codeText, 'skin applet', 'exec')
        except Exception as ex:
            raise SkinError('applet failed to compile: ' + str(ex))

        if widgetType == 'onLayoutFinish':
            screen.onLayoutFinish.append(code)
        elif widgetType == 'onExecBegin':
            screen.onExecBegin.append(code)
        elif widgetType == 'onFirstExecBegin':
            screen.onFirstExecBegin.append(code)
        elif widgetType == 'onShow':
            screen.onShowCode.append(code)
        elif widgetType == 'onHide':
            screen.onHideCode.append(code)
        elif widgetType == 'onClose':
            screen.onCloseCode.append(code)
        else:
            raise SkinError("applet type '%s' unknown!" % widgetType)

    def process_elabel(widget, context):
        n = widget.attrib.get('name')
        w = additionalWidget()
        w.widget = eLabel
        w.skinAttributes = []
        w.name = n
        collectAttributes(w.skinAttributes, widget, context, skin_path_prefix, ignore=('name',))
        screen.additionalWidgets.append(w)

    def process_epixmap(widget, context):
        n = widget.attrib.get('name')
        w = additionalWidget()
        w.widget = ePixmap
        w.skinAttributes = []
        w.name = n
        collectAttributes(w.skinAttributes, widget, context, skin_path_prefix, ignore=('name',))
        screen.additionalWidgets.append(w)

    def process_screen(widget, context):
        for w in widget.getchildren():
            conditional = w.attrib.get('conditional')
            if conditional and not [ i for i in conditional.split(',') if i in screen.keys() ]:
                continue
            p = processors.get(w.tag, process_none)
            try:
                p(w, context)
            except SkinError as e:
                print "[SKIN ERROR] In screen '%s' widget '%s':" % (name, w.tag), e

    def process_panel(widget, context):
        n = widget.attrib.get('name')
        if n:
            try:
                s = dom_screens[n]
            except KeyError:
                print "[SKIN ERROR] Unable to find screen '%s' referred in screen '%s'" % (n, name)
            else:
                process_screen(s[0], context)

        layout = widget.attrib.get('layout')
        if layout == 'stack':
            cc = SkinContextStack
        else:
            cc = SkinContext
        try:
            c = cc(context, getAttribScreen(widget.attrib, 'position'), getAttribScreen(widget.attrib, 'size'), getAttribScreen(widget.attrib, 'font'))
        except Exception as ex:
            raise SkinError('Failed to create skincontext (%s,%s,%s) in %s: %s' % (getAttribScreen(widget.attrib, 'position'),
             getAttribScreen(widget.attrib, 'size'),
             getAttribScreen(widget.attrib, 'font'),
             context,
             ex))

        process_screen(widget, c)

    processors = {None: process_none,
     'widget': process_widget,
     'applet': process_applet,
     'eLabel': process_elabel,
     'ePixmap': process_epixmap,
     'panel': process_panel}
    try:
        context.x = 0
        context.y = 0
        process_screen(myscreen, context)
    except Exception as e:
        print '[SKIN ERROR] In %s:' % name, e

    from Components.GUIComponent import GUIComponent
    nonvisited_components = [ x for x in set(screen.keys()) - visited_components if isinstance(x, GUIComponent) ]
    screen = None
    visited_components = None
    return
