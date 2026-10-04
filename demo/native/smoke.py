"""Exercise the running native demo, including real compositor geometry."""
import json
import os
from pathlib import Path
import shutil
import time

root = Path.home() / '.local/state/convertibled-native-demo'
run = Path((root / 'latest').read_text().strip())
os.environ['DBUS_SESSION_BUS_ADDRESS'] = (run / 'bus-address').read_text().strip()
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

def call(method, scenario=None):
    args = GLib.Variant('(s)', (scenario,)) if scenario else None
    return bus.call_sync('org.convertibled.Demo', '/org/convertibled/Demo',
        'org.convertibled.Demo', method, args, None, Gio.DBusCallFlags.NO_AUTO_START,
        5000, None).unpack()[0]

def scenario(name, check):
    call('Scenario', name)
    for _ in range(60):
        time.sleep(0.1)
        state = json.loads(call('Inspect'))
        if check(state) and (name.startswith('gnome-') or not state.get('nativeOverview', False)):
            time.sleep(0.6)
            capture = call('Capture')
            shutil.copyfile(capture, run / (name + '.png'))
            print(name + ': PASS', flush=True)
            return
    raise AssertionError((name, state))

scenario('home', lambda s: s['home'] and s['dock'] and s['homeIsDesktop'] and all(w['minimized'] for w in s['frames']))
scenario('app', lambda s: s['home'] and not s['desktopExposed'] and any(not w['minimized'] for w in s['frames']))
scenario('tablet', lambda s: not s['desktopExposed'] and any(not w['minimized'] for w in s['frames']))
scenario('minimize-apps', lambda s: s['desktopExposed'])
scenario('overview', lambda s: s['overview'] and s['windows'] >= 2)
scenario('split', lambda s: not s['overview'] and
         len(s['frames']) == 2 and not any(w['minimized'] for w in s['frames']) and s['frames'][0]['x'] != s['frames'][1]['x'])
scenario('gnome-overview', lambda s: s['nativeOverview'] and not s['home'] and not s['dock'] and not s['divider'])
scenario('gnome-apps', lambda s: s['nativeOverview'] and not s['home'] and not s['dock'] and not s['divider'])
scenario('leave-overview', lambda s: not s['nativeOverview'] and s['home'] and s['dock'])
scenario('portrait', lambda s: s['monitor']['height'] > s['monitor']['width'] and
         len(s['frames']) == 2 and s['frames'][0]['y'] != s['frames'][1]['y'])
scenario('landscape', lambda s: s['monitor']['width'] > s['monitor']['height'])
scenario('laptop', lambda s: not s['active'] and not s['dock'] and s['workArea'] == s['monitor']['height'] - 32)
scenario('failure', lambda s: s['failure'] and not s['active'])
scenario('home', lambda s: not s['failure'] and s['active'] and s['home'])
scenario('light', lambda s: s['appearance'] == 'prefer-light')
scenario('large-text', lambda s: s['textScale'] == 1.25)
scenario('normal-text', lambda s: s['textScale'] == 1)
scenario('reduced-motion', lambda s: not s['animations'])
scenario('overview', lambda s: s['overview'])
scenario('normal-motion', lambda s: s['animations'])
scenario('keyboard', lambda s: s['keyboard']['visible'] and s['layout']['compact'] and
         s['layout']['homeBottom'] <= s['layout']['dockTop'] and
         s['layout']['dockBottom'] <= s['monitor']['height'] - s['keyboard']['height'])
scenario('keyboard', lambda s: not s['keyboard']['visible'])
scenario('dark', lambda s: s['appearance'] == 'prefer-dark')
scenario('home', lambda s: s['home'] and not s['layout']['compact'])
scenario('compact', lambda s: s['monitor']['width'] == 480)
scenario('overview', lambda s: s['overview'])
scenario('large-text', lambda s: s['textScale'] == 1.25)
scenario('normal-text', lambda s: s['textScale'] == 1)
scenario('small', lambda s: s['monitor']['height'] == 480)
scenario('home', lambda s: s['desktopExposed'])
scenario('landscape', lambda s: s['monitor']['width'] == 1280)
scenario('home', lambda s: s['desktopExposed'])
print('Native scenario smoke passed. Screenshots: ' + str(run))
