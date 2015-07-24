#!/usr/bin/env python
# coding: utf-8

# the following line is recommended to ease porting to Python 3
#  from __future__ import (absolute_import, division, print_function, unicode_literals)
# todo: uncomment the line above and then fix up all the print commands
import os
import json
import time
import HTMLParser
import threading
import urllib

try:
    import ui
    import console
except ImportError:
    print "Using Dummy UI"
    import dummyUI as ui
    import dummyConsole as console
    
import tag_manager
import themes

DEBUG = True
WEBDELEGATE = None

class DebugDelegate(object):
            def __init__(self, on_load):
                self.on_load = on_load
                
            def webview_should_start_load(self, webview, url, nav_type):
                if "ios-" in url:
                    url = urllib.unquote(url)
                    print url
                    return False
                return True
                
            def webview_did_finish_load(self, webview):
                if self.on_load:
                    self.on_load()


def exception_str(exception):
    return '{}: {}'.format(exception.__class__.__name__, exception)
    
class Parser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.open_tags = []
        self.files_list = []

    def handle_starttag(self, tag, attr):
        if tag == "script":
            for x in attr:
                if "src" in x:
                    self.files_list.append(x[1])
        self.open_tags.append(tag)

    def handle_endtag(self, tag):
        try:
            self.open_tags.remove(tag)
        except ValueError as e:
            print exception_str(e)

    def handle_startendtag(self, tag, attr):
        if tag == "link":
            for x in attr:
                if "href" in x:
                    self.files_list.append(x[1])

    def feed(self, *args, **kwargs):
        self.open_tags = []
        self.files_list = []
        HTMLParser.HTMLParser.feed(self, *args, **kwargs)
        if not self.open_tags == []:
            print "Not all tag/s have been closed.\nOpen tag/s %r" % self.open_tags

@ui.in_background
def show_hide_file_viewer(sender):
    #console.hud_alert("show_hide_file_viewer")
    ss_view = sender.superview.superview
    old_width = ss_view["fileViewContainer"].width
    show = old_width == 0
    width = 188 if show else 0
    x_mod = 8 if show else 0
    ss_view["fileViewContainer"].width = width
    ss_view["fileViewContainer"].set_needs_display()
    ss_view.set_needs_display()

    for subview in ("contentContainer", "toolsContainer"):
        ss_view[subview].x = width + x_mod
        ss_view[subview].width = ss_view.width - width - x_mod
        ss_view[subview].size_to_fit()
        ss_view[subview].set_needs_display()
        for sub in ss_view[subview].subviews:
            sub.size_to_fit()
            sub.set_needs_display()

            try:
                sub.reload()
            except:
                try:
                    sub["web_view"].reload()
                except:
                    pass



@ui.in_background
def server_editor(sender):
    sss_view = sender.superview.superview.superview
    if sss_view:
        sss_view.set_server_editor()
    else:
        console.hud_alert("server_editor")

@ui.in_background
def preview(sender):
    #console.hud_alert("preview")
    p = Parser()
    webdelegate = WEBDELEGATE
    fm = sender.superview.superview.fileManager
    text = sender.superview.superview["contentContainer"]["editor_view"]["WebEditor"]["web_view"].evaluate_javascript("editor.getValue()")
    if webdelegate:
        edit_view = webdelegate.load_console()
        edit_view.name = "Previewer"
        edit_view["console_input"].delegate = webdelegate.WebViewInputDelegate(edit_view["web_view"])
    else:
        edit_view = ui.View()
        wv = ui.WebView()
        wv.name = "web_view"
        wv.flex = "WH"
        edit_view.flex = "WH"
        edit_view.add_subview(wv)
        
    p.feed(text)
    def dummy(*args, **kwagrs):
        pass
    
    def on_load(*args, **kwargs):
        edit_view["web_view"].eval_js("load(%s)" % json.dumps(text))
        for i in p.files_list:
            if i.endswith(".css"):
                add_file = '''
var style = document.createElement("STYLE");
style.setAttribute("type", "text/css");
style.innerHTML = %s;
document.getElementsByTagName("head")[0].appendChild(style);
''' % json.dumps(fm.get_file(i)[1])
                
            elif i.endswith(".js"):
                add_file = '''
var script = document.createElement("SCRIPT");
script.setAttribute("type", "text/javascript");
script.innerHTML = %s;
document.getElementsByTagName("head")[0].appendChild(script);
''' % json.dumps(fm.get_file(i)[1])
            else:
                add_file = ""
            edit_view["web_view"].eval_js(add_file)
    
    if webdelegate:
        edit_view["web_view"].delegate = webdelegate.WebViewDelegate(dummy, edit_view)
        edit_view["web_view"].delegate.add_load_callback(on_load)
        edit_view["web_view"].load_url(webdelegate.load_html_preview_template())
    else:
        edit_view["web_view"].delegate = DebugDelegate(on_load)
        edit_view["web_view"].load_url(os.path.abspath("../EditorView/template.html"))
    edit_view.present("sheet")
    

@ui.in_background
def quitter(sender):
    try:
        result = console.alert("Close", "Close File or Quit", "Close File", "Quit")
        if result == 1:
            if sender.superview.superview:
                sender.superview.superview.on_close_file()
            else:
                console.hud_alert("Close File")
        elif result == 2:
            sender.superview.superview["contentContainer"].active = False
            if sender.superview.superview.superview:
                sender.superview.superview.superview.close()
            else:
                sender.superview.superview.close()
    except KeyboardInterrupt as e:
        print "User canceled the input. " + exception_str(e)

@ui.in_background
def configure(sender):
    sss_view = sender.superview.superview.superview
    if sss_view:
        sss_view.config_view.present("sheet")
        sss_view.config_view.wait_modal()
        tv = sender.superview.superview["contentContainer"]["editor_view"]["WebEditor"]["web_view"]
        config = sss_view.config_view.config

        font_size = config.get_value("editor.font.size")
        gutter = config.get_value("editor.show.gutter")
        style = config.get_value("editor.style")
        margin = config.get_value("editor.print.margin")
        wrap = config.get_value("editor.line.wrap")
        soft_tab = config.get_value("editor.soft.tabs")
        tab_size = config.get_value("editor.tab.size")
        
        fs = '''for (var elm in document.getElementsByClass('.CodeMirror')) {
    elm.style.font_size = '%ipt';"
}''' % font_size
        tv.eval_js("editor.setOption('theme', '%s')" % style)
        tv.eval_js("editor.setOption('tabSize', '%s')" % tab_size)
        tv.eval_js("editor.setOption('indentWithTabs', '%s')" % soft_tab)
        tv.eval_js("editor.setOption('lineWrapping', '%s')" % wrap)
        tv.eval_js("editor.setOption('lineNumbers', '%s')" % gutter)
        
        def recursive_style_set(root):
            try:
                for sub in root.subviews:
                    if sub.name=="log_view":
                        continue
                    set_bg(sub)
            except Exception as e:
                print exception_str(e)
        
        themes_data = themes.get_background_color()
        def set_bg(sub):
            recursive_style_set(sub)
            sub.background_color = themes_data[style]
                
        set_bg(sender.superview.superview.superview)
        print sender.superview.superview.fileViewer
        set_bg(sender.superview.superview.fileViewer)
        
        '''
            value: "",
            mode: "htmlmixed",
            theme: "default",
            indentUnit: 4,
            smartIndent: true,
            tabSize: 4,
            indentWithTabs: false,
            electricChars: true,
            //spceialChars: \[]\,
            //specialCharPlaceholder: function() {},
            rtlMoveVissually: false,
            keyMap: "default",
            //extraKeys: {},
            lineWrapping: false,
            lineNumbers: true,
            firstLineNumber: 1,
            //lineNumberFormatter: function(line) {return ""},
            //gutters: {},
            fixedGutter: true,
            scrollbarStyle: "native",
            coverGutterNextToScrollbar: false,
            inputStyle: "contenteditable",
            readOnly: false,
            showCursorWhenSelecting: true,
            lineWiseCopyCut: true,
            undoDepth: 250,
            historyEventDelay: 1250,
            //tabIndex: 0,
            autofocus: true,
            dragDrop: true,
            cursorBlinkRate: 530,
            cursorScrollMargin: 0,
            cursorHeight: 1,
            resetSelctionOnContextMenu: true,
            workTime: 200,
            workDelay: 300,
            pollInterval: 100,
            flattenSpans: true,
            addModeClass: true,
            maxHighlightLength: 10000,
            viewportMargin: 100,
            matchBrackets: true,
        '''
    else:
        console.alert("Configuration is only available through the Main View")

@ui.in_background
def add_tag(sender):
    v = ui.TableView()
    v.data_source = ui.ListDataSource(tag_manager.TAGS)
    try:
        we = sender.superview.superview["contentContainer"]["editor_view"]["WebEditor"]["web_view"]
    except IndexError as e:
        print exception_str(e)
        we = ui.WebView()
    v.delegate = tag_manager.TagDelegate(we.eval_js)
    v.name = "Add Tag"
    v.width = 350
    v.height = 500
    v.present("popover", popover_location=(sender.superview.x, sender.superview.y))
    v.wait_modal()
    

class Editor(ui.View):
    def __init__(self, *args, **kwargs):
        ui.View.__init__(self, *args, **kwargs)
        self.fileManager = None
        self.fileViewer = None

    def did_load(self):
        print "%r loaded" % self
        print self.superview
        try:
            self.update_config(self.superview.config_view)
        except Exception as e:
            print exception_str(e)

    def set_fv_fm(self, file_manager, file_viewer):
        self.fileManager = file_manager
        self.fileViewer = file_viewer
        self.fileViewer.flex = "WH"
        _, _, w, h = self["fileViewContainer"].frame
        self.fileViewer.frame =(0, 0, 188, h)
        self.fileViewer.bring_to_front()
        self.fileViewer.size_to_fit()
        self.set_needs_display()
        
        #configure(self["menuBarContainer"]["configure"])

    def update_config(self, config_view):
        print "update_config: %r" % config_view
        self["contentContainer"].update_from_config(config_view)

    def apply_fileview(self):
        self["fileViewContainer"].add_subview(self.fileViewer)
        show_hide_file_viewer(self["contentContainer"].subviews[0])
        show_hide_file_viewer(self["contentContainer"].subviews[0])

    def load_file(self, *args):
        self["contentContainer"].add_file(*args)

    def on_close_file(self):
        try:
            self["contentContainer"].on_close_file()
        except Exception as e:  # todo: this should be a qualified exception
            print "Error Closing File. " + exception_str(e)

HTMLEdit = Editor

def save(page_contents, tev):
    try:
        sindex = tev.pagecontrol.selected_index
        page = tev.pagecontrol.segments[sindex]
        tev.superview.fileManager.add_file(page, page_contents)
        if page.endswith(".html"):
            tev.parse_page(None, page, page_contents)

        print "File saved"
        print "%s saved with contents\n%s" % (page, page_contents)
    except Exception as e:
        print "Failed to save. " + exception_str(e)

class ContentContainerView(ui.View):
    def __init__(self, *args, **kwargs):
        ui.View.__init__(self, *args, **kwargs)
        self.html_parser = Parser()

    def did_load(self):
        print "DID LOAD %r" % self
        self.textview = self["editor_view"]
        print self.textview.subviews
        self.filecontrol = self["file_control"]
        self.filecontrol.action = self.select_file
        self.pagecontrol = self["page_control"]
        self.pagecontrol.action = self.select_page

        self.filecontrol.segments = ()
        self.pagecontrol.segments = ()

    def update_from_config(self, config_view):
        tv = self["editor_view"]["WebEditor"]["web_view"]
        config = config_view.config

        font_size = config.get_value("editor.font.size")
        gutter = config.get_value("editor.show.gutter")
        style = config.get_value("editor.style")
        margin = config.get_value("editor.print.margin")
        wrap = config.get_value("editor.line.wrap")
        soft_tab = config.get_value("editor.soft.tabs")
        tab_size = config.get_value("editor.tab.size")
        
        fs = '''for (var elm in document.getElementsByClass('.CodeMirror')) {
    elm.style.font_size = '%ipt';"
}''' % font_size
        tv.eval_js("editor.setOption('theme', '%s')" % style)
        tv.eval_js("editor.setOption('tabSize', '%s')" % tab_size)
        tv.eval_js("editor.setOption('indentWithTabs', '%s')" % soft_tab)
        tv.eval_js("editor.setOption('lineWrapping', '%s')" % wrap)
        tv.eval_js("editor.setOption('lineNumbers', '%s')" % gutter)
        
        def recursive_style_set(root):
            try:
                for sub in root.subviews:
                    recursive_style_set(sub)
                    if style=="3024-day":
                        sub.background_color = "#f7f7f7"
                    elif style=="3024-night":
                        sub.background_color = "#090300"
                    elif style=="3024-day":
                        sub.background_color = "#f7f7f7"
                    elif style=="ambiance" or style=="ambiance-mobile":
                        sub.background_color = "#202020"
                    elif style=="base16-dark":
                        sub.background_color = "#151515"
                    elif style=="base16-light":
                        sub.background_color = "#f5f5f5"
                    elif style=="blackboard":
                        sub.background_color = "#0C1021"
                    elif style=="cobolt":
                        sub.background_color = "#002240"
                    elif style=="colorforth":
                        sub.background_color = "#000000"
                    elif style=="dracular":
                        sub.background_color = "#282a36"
                    elif style=="erlang-dark":
                        sub.background_color = "#002240"
                    elif style=="icecoder":
                        sub.background_color = "#141612"
            except Exception as e:
                print exception_str(e)
                
        recursive_style_set(self.superview)

    def add_file(self, file_path, file_contents):
        if file_path not in self.filecontrol.segments:
            i = list(self.filecontrol.segments)
            i.append(file_path)
            self.filecontrol.segments = i
            self.add_page(file_path)
        self.filecontrol.selected_index = self.filecontrol.segments.index(file_path)
        self.select_file(None)

    def add_page(self, file_path):
        if file_path not in self.pagecontrol.segments:
            i = list(self.pagecontrol.segments)
            i.append(file_path)
            self.pagecontrol.segments = i

    def on_close_file(self):
        segment = self.filecontrol.segments[self.filecontrol.selected_index]
        self.filecontrol.selected_index = self.filecontrol.selected_index - 1
        print segment
        i = list(self.filecontrol.segments)
        i.remove(segment)
        self.filecontrol.segments = i
        self.pagecontrol.segments = ()
        self.select_file(None)

    def close_file(self, file):
        print "Closing file: %s" % (file)
        for page in self.pagecontrol.segments:
            self.pagecontrol.selected_index = self.pagecontrol.segments.indexof(page)
            self.select_page(None)
        self.pagecontrol.segments = tuple("NO OPEN FILE/s")


    def select_file(self, sender):
        try:
            name = self.filecontrol.segments[self.filecontrol.selected_index]
            if self.superview.fileManager:
                self.pagecontrol.segments = ()
                self.add_page(name)
                self.pagecontrol.selected_index = 0
                self.select_page(None)
            else:
                print "Error opening file"
        except Exception as e:
            print "Error loading file " + exception_str(e)
            self.set_editor_value("Error Opening File\n%s" % exception_str(e))


    def select_page(self, sender):
        if self.superview.fileManager:
            name = self.pagecontrol.segments[self.pagecontrol.selected_index]
            file_data = self.superview.fileManager.get_file(name)[1]
            if name.endswith(".html"):
                self.parse_page(sender, name, file_data)

            self.set_editor_value(file_data)
        else:
            self.set_editor_value("Error loading file.\nFileManager not found")

    @ui.in_background
    def parse_page(self, sender, page, file_data):
        self.html_parser.feed(file_data)
        print self.html_parser.files_list
        print list(self.pagecontrol.segments[1:])
        if self.html_parser.files_list != list(self.pagecontrol.segments[1:]):
            self.pagecontrol.segments = ()
            self.add_page(page)
            for file in self.html_parser.files_list:
                if file:
                    self.add_page(file)
            self.pagecontrol.selected_index = 0
        if self.html_parser.open_tags:
            self.superview["toolsContainer"]["open_tags"].text = "Open Tags: %s" % ", ".join(self.html_parser.open_tags)
            self.superview["toolsContainer"]["open_tags"].line_break_mode = ui.LB_CHAR_WRAP
            self.superview["toolsContainer"]["open_tags"].size_to_fit()
        else:
            self.superview["toolsContainer"]["open_tags"].text = "No open tags"
            self.superview["toolsContainer"]["open_tags"].line_break_mode = ui.LB_CHAR_WRAP
            self.superview["toolsContainer"]["open_tags"].size_to_fit()
 
    @ui.in_background
    def set_editor_value(self, text):
        we = self["editor_view"]["WebEditor"]["web_view"]
        try:
            name = self.pagecontrol.segments[self.pagecontrol.selected_index]
        except IndexError as e:
            print exception_str(e)
            name = "ERROR.txt"
        we.delegate.open(name, text)



class PropertiesView(ui.View):
    def __init__(self, *args, **kwargs):
        ui.View.__init__(self, *args, **kwargs)


def load_editor(file_manager=None, file_viewer=ui.View(), frame=(0, 0, 540, 600), webdelegate=None):
    try:
        view = ui.load_view("HTMLEditor/__init__")
    except ValueError as e:
        print "Attempt 1 'HTMLEditor/__init__' failed " + exception_str(e)
        try:
            view = ui.load_view("__init__")
        except ValueError as e:
            print "Attempt 2 '__init__' failed " + exception_str(e)
            view = ui.Editor()
    view.frame = frame
    view.set_fv_fm(file_manager, file_viewer)
    view.size_to_fit()
    view.set_needs_display()

    vx,vy,vw,vh = view["contentContainer"]["editor_view"].frame
    width = vw
    height = vh

    if webdelegate:
        global WEBDELEGATE
        WEBDELEGATE = webdelegate
        def save_func(contents):
            save(contents, view["contentContainer"])
        if DEBUG:
            edit_view = webdelegate.load_console()
            edit_view.name = "WebEditor"
            edit_view["console_input"].delegate = webdelegate.WebViewInputDelegate(edit_view["web_view"])
        else:
            edit_view = webdelegate.load_editor_view()
            edit_view.name = "WebEditor"
            
        edit_view["web_view"].delegate = webdelegate.WebViewDelegate(save_func, edit_view)
        edit_view["web_view"].load_url(webdelegate.load_html_editor_view())
    else:
        edit_view = ui.View()
        edit_view.name = "WebEditor"
        wv = ui.WebView()
        wv.delegate = DebugDelegate(None)
        wv.name = "web_view"
        wv.flex = "WH"
        edit_view.add_subview(wv)
        d = os.path.abspath("../EditorView/index.html")
        print "Load: %r" % d
        edit_view["web_view"].load_url(d)
        
    edit_view.flex = "WH"
    edit_view.size_to_fit()
    edit_view.frame = (0, 0, width, height)
    edit_view.set_needs_display()

    view["contentContainer"]["editor_view"].add_subview(edit_view)
    view["contentContainer"]["editor_view"].size_to_fit()
    view["contentContainer"]["editor_view"].set_needs_display()

    return view


__all__ = ["load_editor", "Editor", "HTMLEdit", "TextEditorView", "PropertiesView"]

if __name__ == "__main__":
    view = load_editor()
    view.present("sheet" if DEBUG else "fullscreen", hide_title_bar=not DEBUG)