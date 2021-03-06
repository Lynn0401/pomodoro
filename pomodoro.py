import sys
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.vector import Vector
from kivy.properties import (NumericProperty, StringProperty,
                             ListProperty, BooleanProperty)
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.audio import SoundLoader
from kivy.config import Config
from kivy.uix.screenmanager import SlideTransition
from kivy.utils import get_color_from_hex
from time import strftime, gmtime
from kivy.uix.scatter import Scatter
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from datetime import datetime
from requests import get as REQ_GET
from copy import copy
from config import *


def get_buttons(obj, buttons=[]):
    """
    Buttons which are capable of hover action will
    taken from the root object. Capability is kept
    with buttons extra attribute called 'has_hover'
    """
    for ch in obj.children:
        if hasattr(ch, 'has_hover') and \
                hasattr(ch, 'ranged') and \
                ch.has_hover:
            buttons.append(ch)
        get_buttons(ch, buttons)
    return buttons


class LogItem(BoxLayout):

    """
    BranchesItem; on branches screen, on other branches list,
    each element is using this class to display.
    """
    date = StringProperty("")
    log = StringProperty("")
    index = NumericProperty()

    def __del__(self, *args, **kwargs):
        pass

    def show_log(self, index):
        pomodoro = self.parent.parent.parent.parent.parent.parent.parent.parent
        pomodoro.show_log(index)

class CustomSpinner(Spinner):

    """
    Base Spinner class has _on_dropdown_select method which holds
    only change the text attribute of class which is not enough.

    CustomSpinner used to display log dates only.
    """

    def __del__(self, *args, **kwargs):
        pass

    def _on_dropdown_select(self, instance, data, *largs):
        self.text = "[color=%s]%s[/color]"%(self.color_data, data)
        pomodoro = self.parent.parent.parent.parent
        pomodoro.load_logs(date = data)

class MyScatterLayout(ScatterLayout):

    """
    Using scatter as slider.
    """
    rstop = BooleanProperty(False)
    lstop = BooleanProperty(False)
    pre_posx = NumericProperty()
    grab_posx = NumericProperty()
    current_posx = NumericProperty()

    def on_touch_move(self, touch):
        """
        Movement should be in between given positions.
        For this app. positions are static.
        """
        possibility = self.grab_posx + (touch.pos[0] - self.pre_posx)
        if touch.grab_list:
            if -10 <= possibility <= 150:
                super(MyScatterLayout, self).on_touch_move(touch)
                self.current_posx = possibility
                pomodoro = self.parent.parent.parent.parent.parent
                volume = (1 / float((150 + 10))) * self.pos[0]
                pomodoro.clock.volume = volume
                pomodoro.alarm.volume = volume

    def on_touch_down(self, touch):
        """
        To understand the image movement, to left or to right;
        previous position must be kept and keep updating.
        """
        super(MyScatterLayout, self).on_touch_down(touch)
        self.pre_posx = touch.pos[0]
        self.grab_posx = self.pos[0]


class Pomodoro(BoxLayout):
    time_period = NumericProperty()
    rotation = NumericProperty(0)
    sprint_count = NumericProperty(0)

    time_display = StringProperty()
    time_minute = StringProperty()
    time_second = StringProperty()
    state = StringProperty()
    start = StringProperty()
    stop = StringProperty()

    logs = ListProperty([])

    server_url = StringProperty()
    #"http://172.18.140.79:8000/api/v1.0/put/pomodoro"
    server_user = StringProperty("barbaros")

    server_send = BooleanProperty(False)
    count_start = BooleanProperty(False)
    connect_server = BooleanProperty(False)

    buttons = ListProperty()

    def __init__(self, *args, **kwargs):
        super(Pomodoro, self).__init__(*args, **kwargs)
        self.buttons = get_buttons(self, [])
        self.animation = None
        self.clock = SoundLoader.load('assets/clock.wav')
        self.alarm = SoundLoader.load('assets/alarm.wav')
        self.load_log_dates()
        #self.load_logs()
        try:
            last_session = DB.store_get('last_session')
        except KeyError:
            last_session = ""
        if last_session:
            self.set_restart_session(last_session)
        else:
            self.set_to_workstate()

        if ACTIVE_STYLE == "style1":
            self.sm.current = 'start'

    def show_log(self, index):
        """
        show_log, to display specified log with more
        information and full log content.
        """
        data = self.logs[index]
        self.switch_screen('logdetail_screen', side='down')
        floatlayout = self.sm.current_screen.children[0]
        floatlayout.log_detail.text = data['content']
        floatlayout.date_distance.text = "[color=%s]%s - %s[/color]"%(
                                        floatlayout.date_distance.color_data,
                                        data['date_from'].split(' ')[1],
                                        data['date_to'].split(' ')[1])

    def db_check(self):
        """
        db_check, json data can be damaged as objects on it
        to make it back to json serializable dict function called.
        """
        keys = DB.keys()
        for k in keys:
            value = DB.store_get(k)
            if type(value) == list:
                for v in value:
                    if type(v) == dict:
                        if 'date_from' in v:
                            v['date_from'] = str(v['date_from'])
                        if 'date_to' in v:
                            v['date_to'] = str(v['date_to'])

    def load_log_dates(self):
        """
        load_log_dates, is for picking log days only and
        serving as sorted reversely.
        """
        days = list(set(filter(lambda x: len(x.split("-"))==3, DB.keys())))
        days.sort(reverse=True)
        self.log_spinner.values = days

    def load_logs(self, date=""):
        """
        load_logs, according to the given date required
        data set is taken and serves to app.
        """
        logs = []
        days = filter(lambda x: len(x.split("-"))==3, DB.keys())
        for day in days:
            data = DB.store_get(day)
            DB.store_sync()
            for log in data:
                if type(log['date_from']) != datetime:
                    log['date_from'] = datetime.strptime(log['date_from'],
                                                "%Y-%m-%d %H:%M:%S")
                if type(log['date_to']) != datetime:
                    log['date_to'] = datetime.strptime(log['date_to'],
                                                "%Y-%m-%d %H:%M:%S")
            if day == date:
                logs.extend(data)
        logs.sort(key=lambda x: x['date_from'], reverse=True)
        counter = 0
        for log in logs:
            log['index'] = logs.index(log)
        self.logs = logs
        self.db_check()

    def set_restart_session(self, dct):
        """
        To restore previously stored, because of restart
        operation, data. Not to reach the same session
        after restoring operation the data must be deleted.
        """
        self.message.text = dct['message_text']
        self.message.disabled = dct['message_disabled']
        self.server_url = dct['server_url']
        self.count_start = dct['count_start']
        self.state = dct['state']
        self.time_period = dct['time_period']
        self.start = dct['start']
        self.stop = dct['stop']

        state = self.state
        if self.state in ("paused", "work"):
            self.set_to_workstate(period=self.time_period)
        else:
            self.set_to_breakstate(period=self.time_period)

        if self.count_start:
            if self.state == "break":
                self.message.disabled = False
                self.message.focus = True
                if ACTIVE_STYLE == "style3":
                    self.message.background_color = get_color_from_hex(
                        "ffffff")
            else:
                self.start_animation()
        else:
            self.disable_buttons()
        if state == "paused":
            self.pause_but.disabled = True

        DB.store_delete('last_session')
        self.db_check()
        DB.store_sync()

    def disable_buttons(self):
        """
        play, stop and pause buttons disability attr. handler.
        """
        buttons = [self.play_but,
                   self.stop_but,
                   self.pause_but]
        for but in buttons:
            but.disabled = False

    def start_animation(self):
        """
        starts animation for rotation, if state is on 'work'
        then start date should be taken to log pomodoro.
        other then stop date must be reset in each starting animation action.
        """
        if self.state == "work":
            self.count_start = True
            self.start = str(datetime.now()).rsplit('.', 1)[0]

        elif self.state == "paused" and ACTIVE_STYLE in ("style2", "style3"):
            self.pause_but.disabled = False
            self.state = "work"
            self.count_start = True
        self.disable_buttons()
        self.stop = ""
        if self.state == "break":
            self.pause_but.disabled = True
            self.pause_but.inactive = True
            self.play_but.disabled = True
            self.play_but.inactive = True

        if not self.server_send:
            self.send_data()
        Clock.schedule_once(lambda dt: self.decrease_minutes(), 1)
        if ACTIVE_STYLE == "style1":
            self.start_button.disabled = True
        if ACTIVE_STYLE in ("style2", "style3"):
            self.play_but.disabled = True
            self.message.disabled = True
            self.message.focus = False
            if ACTIVE_STYLE == "style3":
                self.message.background = (0.078, 0.090, 0.094, 1)

    def decrease_minutes(self):
        """
        until the rotation count reaches the end
        minutes and rotation should be continue.
        At the end pomodoro stop date must be taken too
        sounds should also be handled.
        """
        if not self.count_start:
            pass
        elif self.time_period < 1:
            self.rotation = 0
            self.reset_time()
        else:
            self.clock.stop()
            self.clock.play()

            self.rotation += self.perrotation
            self.time_period -= 1
            self.time_display = strftime('%M:%S', gmtime(self.time_period))
            self.time_minute, self.time_second = self.time_display.split(':')
            if not self.server_send:
                self.send_data()
            if ACTIVE_STYLE == "style1":
                if self.animation:
                    self.animation.stop(self)
                self.animation = Animation(rotation=self.rotation, d=1)
                self.animation.start(self)

            if self.state == "work" and self.time_period < 1:
                self.stop = str(datetime.now()).rsplit('.', 1)[0]

            Clock.schedule_once(lambda dt: self.decrease_minutes(), 1)

    def send_data(self, state=""):
        """
        To update server side info, if requested.
        """
        result = True
        if self.server_url and self.server_user:
            state_time = {"work": 1500, "break": 300, "stop": 1800}
            total_time = state_time[state] if state else state_time[self.state]
            result = REQ_GET(self.server_url,
                             params={"user": self.server_user,
                                     "total": total_time,
                                     "now": self.time_period,
                                     "state": self.state},
                             timeout=1,)
            self.server_send = result
        return result

    def pause_animation(self):
        """
        To pause the timer. in this change of state
        if server side visuality wanted, updater should be called.
        """
        self.count_start = False
        self.clock.stop()
        self.alarm.stop()
        state = self.state
        self.state = 'paused'
        self.disable_buttons()
        self.pause_but.disabled = True
        if self.server_url and self.server_user:
            while True:
                res_result = self.send_data(state=state)
                if res_result.status_code == 200:
                    break
        self.server_send = False

    def stop_animation(self):
        """
        To stop the timer. in this change of state
        if server side visuality wanted, updater should be called.
        """
        self.count_start = False
        self.clock.stop()
        self.alarm.stop()
        if self.server_url and self.server_user:
            self.state = "stop"
            while True:
                res_result = self.send_data()
                if res_result.status_code == 200:
                    break
        self.set_to_workstate()
        self.message.text = ""
        if ACTIVE_STYLE == "style3":
            self.message.background_color = (0.078, 0.090, 0.094, 1)
        self.message.disabled = True
        self.disable_buttons()
        self.server_send = False

    def switch_screen(self, screen, side=None):
        """
        action screens rotation handling
        """
        direction = 'up'
        if ACTIVE_STYLE in ("style2", "style3") and \
                self.sm.current == self.sm.settings_screen.name:
            direction = 'down'
        if side:
            direction = side
        self.sm.transition = SlideTransition(direction=direction)
        self.sm.current = screen
        self.buttons = get_buttons(self, [])

    def set_clock(self):
        """
        rotation for per second calculation.
        """
        if self.time_period:
            self.perrotation = Vector(1, 1).angle(
                Vector(1, 1).rotate(360 / float(self.time_period)))

    def set_to_workstate(self, period=None):
        """
        the state of pomodoro taken to 'work' time periods and
        required settings handled. for per work pomodoro
        counter counts this state until break state triggered
        """
        self.state = "work"
        self.time_period = WORK_TIME_PERIOD if period == None else period
        self.time_display = strftime('%M:%S', gmtime(self.time_period))
        self.time_minute, self.time_second = self.time_display.split(':')
        self.sprint_count += 1
        self.set_clock()
        if ACTIVE_STYLE == "style1":
            self.switch_screen('start')

    def set_to_breakstate(self, period=None):
        """
        Break pomodoro action handled, the time calculated by
        the work state counter then it resets
        """
        self.state = "break"
        self.time_period = (
            BREAK_TIME_PERIOD * self.sprint_count) if period == None else period
        self.sprint_count = 0
        self.time_display = strftime('%M:%S', gmtime(self.time_period))
        self.time_minute, self.time_second = self.time_display.split(':')
        self.set_clock()
        if ACTIVE_STYLE == "style1":
            self.switch_screen('start')

    def reset_time(self):
        """
        triggered when the timer reaches the end, animation, clock sound,
        disability of button switched to other state of each.
        pomodoro state changes according to the current one.
        If the current state is 'break' then 'work' state trigger triggered
        """
        if self.animation:
            self.animation.stop(self)
        self.rotation = 0
        self.clock.stop()
        self.alarm.play()
        if ACTIVE_STYLE == "style1":
            self.start_button.disabled = False
        elif ACTIVE_STYLE in ("style2", "style3"):
            self.disable_buttons()
            if self.state == "work":
                self.state = "break"
                self.set_to_breakstate()

                self.message.disabled = False
                self.message.focus = True
                if ACTIVE_STYLE == "style3":
                    self.message.background_color = get_color_from_hex(
                        "ffffff")

                self.play_but.disabled = True
                self.pause_but.disabled = True
                self.play_but.inactive = True
                self.pause_but.inactive = True
            elif self.state == "break":
                self.set_to_workstate()
                self.message.text = ""
        if ACTIVE_STYLE == "style1":
            if self.state == "break":
                self.switch_screen('start')
                self.set_to_workstate()
            else:
                self.switch_screen('info')

    def set_volume(self, state):
        """
        Volume operation handled except alarm sound.
        """
        on_off = 0 if state == "down" else 1
        if self.clock:
            self.clock.volume = on_off

    def keep_info(self, text=None):
        """
        after each pomodoro in 'work' state an information is taken
        from user and to log that with other necessary informations
        collection is written in a file.
        """
        if not text:
            text = self.message.text.strip()

        if text:
            if ACTIVE_STYLE == "style3":
                self.message.background_color = (0.078, 0.090, 0.094, 1)

            data = dict(date_from=self.start,
                        date_to=self.stop,
                        content=text,
                        is_sent=False)
            if ACTIVE_STYLE == "style1":
                self.message.text = ""
            current_day = self.start.rsplit(" ", 1)[0]
            try:
                existing_data = DB.store_get(current_day)
            except KeyError:
                existing_data = []
            existing_data.append(data)
            DB.store_put(current_day, existing_data)
            self.db_check()
            self.load_log_dates()
            DB.store_sync()
            if ACTIVE_STYLE == "style1":
                self.switch_screen('action')
            elif ACTIVE_STYLE in ("style2", "style3"):
                self.start_animation()

    def update_connect_server(self):
        self.connect_server = not self.connect_server
        if self.connect_server:
            self.switch_screen(server_screen, side='right')

    def set_server_user(self):
        pass

    def set_server_url(self):
        pass

    def on_mouse_pos(self, *args):
        """
        hover action handling, for capable buttons.
        """
        mouse_position = args[1]

        if self.sm.current == 'log_screen':
            #items = self.sm.children[0].children[0].logs.children[0].children[0].children
            pass
        else:
            buttons = filter(lambda x:
                             x.pos[0] <= mouse_position[0] <= x.ranged[0] and
                             x.pos[1] <= mouse_position[1] <= x.ranged[1],
                             self.buttons)
            button = None
            if buttons and 149 > mouse_position[1] > 1 and \
                    299 > mouse_position[0] > 1:
                button = buttons[0]
            for but in self.buttons:
                if but != button:
                    but.inactive = True
                else:
                    but.inactive = False

    def change_theme(self):
        theme = DB.store_get("theme")
        if theme == 'style3':
            theme = 'style2'
            self.toggle_source.source = "assets/icons/switches_to_dark.png"
        else:
            theme = 'style3'
            self.toggle_source.source = "assets/icons/switches_to_light.png"
        DB.store_put('theme', theme)
        self.db_check()
        DB.store_sync()
        Clock.schedule_once(lambda dt: self.restart(), .5)

    def to_dict(self):
        """
        To store required data from restoring app and
        loosing all, values packed in a dict.
        """
        return {'state': self.state,
                'count_start': self.count_start,
                'server_url': self.server_url,
                'server_user': self.server_user,
                'message_text': self.message.text,
                'message_disabled': self.message.disabled,
                'time_period': self.time_period,
                'start': str(self.start),
                'stop': str(self.stop)}

    def restart(self):
        """
        Restoring current values to specified file on
        config.py and restart operation of app handled.
        """
        DB.store_put('last_session', self.to_dict())
        self.db_check()
        DB.store_sync()
        args = sys.argv[:]
        args.insert(0, sys.executable)
        os.execv(sys.executable, args)

    def log_converter(self, row_index, item):
        data = {
            'log': item['content'],
            'date': str(item['date_from'].split(" ")[1].strip()),
            'index': item['index']
        }
        return data


class PomodoroApp(App):

    def __init__(self, *args, **kwargs):
        super(PomodoroApp, self).__init__(*args, **kwargs)
        styles = {"style1": STYLE1, "style2": STYLE2, "style3": STYLE3}
        Builder.load_file(styles[ACTIVE_STYLE])
        self.icon = ICON_PATH
        self.title = "Pomodoro"

    def build(self):
        layout = Pomodoro()
        if ACTIVE_STYLE in ("style2", "style3"):
            Window.bind(mouse_pos=layout.on_mouse_pos)
        return layout

if __name__ == "__main__":
    """
    Window sizes and wanted skills are set, then app calls
    """
    styles = {"style1": WINDOW_SIZE_1,
              "style2": WINDOW_SIZE_2,
              "style3": WINDOW_SIZE_2}
    Window.size = styles[ACTIVE_STYLE]
    if ACTIVE_STYLE == "style3":
        Window.clearcolor = (get_color_from_hex("141718"))
    else:
        Window.clearcolor = (.98, .98, .98, 1)
    Window.borderless = False
    Config.set('kivy', 'desktop', 1)
    Config.set('graphics', 'fullscreen', 0)
    Config.set('graphics', 'resizable', 0)

    PomodoroApp().run()
