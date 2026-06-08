from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
import os
import string
import subprocess
import time
import shutil
import ctypes, sys
import configparser
import platform
from datetime import datetime

# ================= VERSION =================

APP_NAME = 'WDIR'
APP_VERSION = '1.00'

# ================= WINDOW =================

window = Tk()
window.title(APP_NAME)
window.state('zoomed')
window.configure(bg='black')

# ================= ICON SETTING =================
icon_data = """
    R0lGODlhEAAQALMAAAAAAIAAAACAAICAAAAAgIAAgQCAgMDAwICAgP8AAAD/AP//AAAA//8A/wD/
    /////ywAAAAAEAAQAAAEMhDISau9OOvNu/9gKI5kaZ5oqq5s675wLM90bd94ru987//AoHBILBqP
    xyRyWTw6nw0EADs=
"""
try:
    img_icon = PhotoImage(data=icon_data)
    window.iconphoto(True, img_icon)
except:
    pass

# ================= CONFIG (INI FILE) =================

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(os.path.realpath(sys.executable))
else:
    base_dir = os.path.dirname(os.path.realpath(__file__))

INI_FILE = os.path.join(base_dir, 'wdir_config.ini')
config = configparser.ConfigParser()

default_keys = {
    'F1': '', 'F2': '', 'F3': '', 'F4': '',
    'F5': '', 'F6': '', 'F7': '', 'F8': '', 'F9': '', 'F10': '', 'F11': '', 'F12': ''
}

if not os.path.exists(INI_FILE):
    config['KEY_MAPPING'] = default_keys
    with open(INI_FILE, 'w', encoding='utf-8') as configfile:
        config.write(configfile)
else:
    config.read(INI_FILE, encoding='utf-8')
    if 'KEY_MAPPING' not in config:
        config['KEY_MAPPING'] = default_keys
    # F12 키 항목 없으면 추가
    if 'F12' not in config['KEY_MAPPING']:
        config['KEY_MAPPING']['F12'] = ''
        with open(INI_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)

# ================= COLORS =================

COLOR_DIR    = 'red'
COLOR_FILE   = 'gray70'
COLOR_DRIVE  = 'dark orange'
COLOR_BG     = 'black'
COLOR_FG     = 'green'
COLOR_MARKED = 'white'

W_BG        = '#f3f3f3'
W_PANEL     = '#ffffff'
W_FG        = '#1a1a1a'
W_BORDER    = '#d0d0d0'
W_ACCENT    = '#0078d4'
W_ACCENT_FG = '#ffffff'
W_HOVER     = '#e5f1fb'
W_TITLE_BG  = '#0078d4'
W_TITLE_FG  = '#ffffff'
W_BTN_BG    = '#0078d4'
W_BTN_FG    = '#ffffff'
W_BTN_HOV   = '#106ebe'
W_BTN2_BG   = '#f3f3f3'
W_BTN2_FG   = '#1a1a1a'
W_ENTRY_BG  = '#ffffff'
W_ENTRY_FG  = '#1a1a1a'

# ================= DRIVES =================

_drives = []
for d in string.ascii_uppercase:
    drive = f'{d}:\\'
    if os.path.exists(drive):
        _drives.append(drive)
if not _drives:
    _drives = ['C:\\']

run_ext = [
    '.exe', '.txt', '.png', '.jpg',
    '.jpeg', '.gif', '.bmp',
    '.mp4', '.avi', '.mkv', '.mov'
]

# ================= STATE =================

left_items = []
right_items = []
left_types = []
right_types = []
left_marked = set()
right_marked = set()
active = None
current_path = _drives[0]
f1_menu = None
menu_mode = False
menu_index = 0
menu_labels = []
footer_base_text = ''
current_dir_count = 0
current_file_count = 0

# ================= MENU BAR =================

menubar = Frame(window, bg=W_BG, relief='flat', bd=0)
menubar.pack(fill='x', side='top')
Frame(window, bg=W_BORDER, height=1).pack(fill='x', side='top')

def make_menu_popup(parent_btn, items):
    popup = Toplevel(window)
    popup.overrideredirect(True)
    popup.configure(bg=W_BG)
    popup.tk_setPalette(background=W_BG)
    parent_btn.update_idletasks()
    x = parent_btn.winfo_rootx()
    y = parent_btn.winfo_rooty() + parent_btn.winfo_height()
    popup.geometry(f'+{x}+{y}')
    Frame(popup, bg=W_BORDER, padx=1, pady=1).pack(fill='both', expand=True)
    inner = Frame(popup, bg=W_PANEL, padx=2, pady=4)
    inner.pack(fill='both', expand=True, padx=1, pady=1)

    def close_popup(event=None):
        popup.destroy()

    for item in items:
        if item is None:
            Frame(inner, bg=W_BORDER, height=1).pack(fill='x', padx=8, pady=3)
        else:
            label_text, callback = item
            lbl = Label(inner, text=label_text, bg=W_PANEL, fg=W_FG,
                        font=('굴림', 10), anchor='w', padx=14, pady=5,
                        cursor='hand2', width=26)
            lbl.pack(fill='x')
            def on_enter(e, l=lbl): l.config(bg=W_HOVER)
            def on_leave(e, l=lbl): l.config(bg=W_PANEL)
            def on_click(e, cb=callback):
                popup.destroy()
                if cb: cb()
            lbl.bind('<Enter>', on_enter)
            lbl.bind('<Leave>', on_leave)
            lbl.bind('<Button-1>', on_click)

    popup.bind('<FocusOut>', close_popup)
    popup.focus_set()

def show_file_menu(btn):
    items = [('새 폴더 Ctrl+N ', make_directory),
             None,
             ('끝내기 Alt+F4', lambda: window.destroy())]
    make_menu_popup(btn, items)

def show_edit_menu(btn):
    items = [
        ('선택/해제 Space ',  lambda: toggle_space_mark(None)),
        None,
        ('복사 Ctrl+C ', copy_items),
        ('이동 Ctrl+M ', move_items),
        ('삭제 Ctrl+D ', delete_items),
        ('이름 바꾸기 Ctrl+R ', rename_item),
    ]
    make_menu_popup(btn, items)

def show_function_menu(btn):
    items = [
        ('메모장으로 열기 Ctrl+E ', open_with_notepad_click),
        ('탐색기로 열기 Ctrl+W ', open_explorer_here),
        ('CMD(관리자권한) Ctrl+O ', open_cmd_here),
        None,
        ('시스템 정보 Ctrl+I ', show_sysinfo_window),
    ]
    make_menu_popup(btn, items)

def show_setting_menu(btn):
    items = [('기능키 설정', show_setting_window)]
    make_menu_popup(btn, items)

def show_help_menu(btn):
    items = [
        ('매뉴얼', show_manual_window),
        None,
        (f'{APP_NAME} 정보', show_about_window),
    ]
    make_menu_popup(btn, items)

_menu_defs = [
    ('파일(F)', lambda b: show_file_menu(b)),
    ('편집(E)', lambda b: show_edit_menu(b)),
    ('기능(C)', lambda b: show_function_menu(b)),
    ('설정(S)', lambda b: show_setting_menu(b)),
    ('도움말(H)', lambda b: show_help_menu(b)),
]

for label, handler in _menu_defs:
    btn = Label(menubar, text=label, bg=W_BG, fg=W_FG,
                font=('굴림', 10), padx=10, pady=5, cursor='hand2')
    btn.pack(side='left')
    btn.bind('<Enter>', lambda e, b=btn: b.config(bg=W_HOVER))
    btn.bind('<Leave>', lambda e, b=btn: b.config(bg=W_BG))
    btn.bind('<Button-1>', lambda e, b=btn, h=handler: h(b))

# ================= TOP BAR =================

topbar = Frame(window, bg='navy')
topbar.pack(fill='x', side='top')

# F1~F12 모두 기능키 (종료 없음)
function_keys = ['F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12']
topbar_labels = {}

# ================= MAIN =================

main = Frame(window, bg=COLOR_BG)
main.pack(fill='both', expand=True)

left_lb = Listbox(main, bg=COLOR_BG, fg=COLOR_FG, selectbackground='darkgreen',
                  selectforeground='white', activestyle='none',
                  font=('굴림', 11), exportselection=False)
left_lb.pack(side='left', fill='both', expand=True)

right_lb = Listbox(main, bg=COLOR_BG, fg=COLOR_FG, selectbackground='darkgreen',
                   selectforeground='white', activestyle='none',
                   font=('굴림', 11), exportselection=False)
right_lb.pack(side='right', fill='both', expand=True)

def block_up(event):
    if menu_mode: return 'break'
    return None

def block_down(event):
    if menu_mode: return 'break'
    return None

left_lb.bind('<Up>', block_up)
left_lb.bind('<Down>', block_down)
right_lb.bind('<Up>', block_up)
right_lb.bind('<Down>', block_down)

# ================= FOOTER =================

footer = Frame(window, bg='medium sea green')
footer.pack(fill='x', side='bottom')

footer_label = Label(footer, bg='medium sea green', fg='white',
                     font=('굴림', 10, 'bold'), anchor='w')
footer_label.pack(side='left', padx=10)

# ================= DRIVE INFO =================

def format_size(size):
    tb = 1024 ** 4
    gb = 1024 ** 3
    if size >= tb: return f'{size / tb:.2f} TB'
    return f'{size / gb:.2f} GB'

def drive_info(path):
    try:
        drive = os.path.splitdrive(path)[0] + '\\'
        total, used, free = shutil.disk_usage(drive)
        return f'DRIVE {drive} ({format_size(total)} / {format_size(free)})'
    except:
        return 'DRIVE UNKNOWN'

# ================= INSERT =================

def insert_left(text, path, ftype):
    if ftype == 'DIR': color = COLOR_DIR
    elif ftype == 'FILE': color = COLOR_FILE
    elif ftype == 'DRIVE': color = COLOR_DRIVE
    else: color = COLOR_FG
    index = left_lb.size()
    left_lb.insert(END, text)
    left_lb.itemconfig(index, fg=color)
    left_items.append(path)
    left_types.append(ftype)

def insert_right(text, path, ftype):
    if ftype == 'DIR': color = COLOR_DIR
    elif ftype == 'FILE': color = COLOR_FILE
    elif ftype == 'DRIVE': color = COLOR_DRIVE
    else: color = COLOR_FG
    index = right_lb.size()
    right_lb.insert(END, text)
    right_lb.itemconfig(index, fg=color)
    right_items.append(path)
    right_types.append(ftype)

# ================= FOOTER / CLOCK =================

def update_footer():
    global footer_base_text
    count_text = f'{current_dir_count} DIR / {current_file_count} FILES'
    footer_base_text = f'{drive_info(current_path)} | {count_text}'

def update_clock():
    try:
        import ctypes as _ct
        class SYSTEMTIME(_ct.Structure):
            _fields_ = [('wYear',_ct.c_ushort),('wMonth',_ct.c_ushort),
                        ('wDayOfWeek',_ct.c_ushort),('wDay',_ct.c_ushort),
                        ('wHour',_ct.c_ushort),('wMinute',_ct.c_ushort),
                        ('wSecond',_ct.c_ushort),('wMilliseconds',_ct.c_ushort)]
        st = SYSTEMTIME()
        _ct.windll.kernel32.GetLocalTime(_ct.byref(st))
        ts = f'{st.wYear:04d}-{st.wMonth:02d}-{st.wDay:02d}  {st.wHour:02d}:{st.wMinute:02d}:{st.wSecond:02d}'
    except:
        ts = datetime.now().strftime('%Y-%m-%d  %H:%M:%S')
    footer_label.config(text=f'{footer_base_text} | {ts}')
    window.after(1000, update_clock)

# ================= 공통 다이얼로그 헬퍼 =================

def make_dialog(title_text, width=460, height=210):
    win = Toplevel(window)
    win.title(title_text)
    win.configure(bg=W_BG)
    win.resizable(False, False)
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    win.geometry(f'{width}x{height}+{int(screen_w/2-width/2)}+{int(screen_h/2-height/2)}')
    win.transient(window)
    win.grab_set()

    tbar = Frame(win, bg=W_TITLE_BG, height=38)
    tbar.pack(fill='x', side='top')
    tbar.pack_propagate(False)
    Label(tbar, text=title_text, bg=W_TITLE_BG, fg=W_TITLE_FG,
          font=('굴림', 11, 'bold')).pack(side='left', padx=16, pady=8)

    body = Frame(win, bg=W_BG, padx=20, pady=14)
    body.pack(fill='both', expand=True)
    return win, body

def w_button(parent, text, command, primary=True):
    bg = W_BTN_BG if primary else W_BTN2_BG
    fg = W_BTN_FG if primary else W_BTN2_FG
    hov = W_BTN_HOV if primary else W_HOVER
    b = Button(parent, text=text, bg=bg, fg=fg,
               activebackground=hov, activeforeground=fg,
               font=('굴림', 10), width=9, bd=0, relief='flat',
               cursor='hand2', command=command)
    b.bind('<Enter>', lambda e: b.config(bg=hov))
    b.bind('<Leave>', lambda e: b.config(bg=bg))
    return b

def w_entry(parent, width=48):
    e = Entry(parent, bg=W_ENTRY_BG, fg=W_ENTRY_FG,
              insertbackground=W_FG, relief='solid', bd=1,
              font=('굴림', 11), width=width)
    return e

# ================= ABOUT WINDOW =================

def show_about_window():
    about, body = make_dialog(f'About {APP_NAME}', width=440, height=220)

    Label(body, text=APP_NAME, bg=W_BG, fg=W_ACCENT,
          font=('굴림', 14, 'bold')).pack(pady=(6, 2))
    Frame(body, bg=W_BORDER, height=1).pack(fill='x', pady=6)
    Label(body, text='Copyright (C) 2026  Myung-Hoon Hwang', bg=W_BG, fg=W_FG,
          font=('굴림', 10)).pack(pady=2)
    Label(body, text=f'Version {APP_VERSION}', bg=W_BG, fg='#666666',
          font=('굴림', 9)).pack(pady=2)

    bf = Frame(body, bg=W_BG)
    bf.pack(pady=10)
    btn = w_button(bf, '확인', about.destroy, primary=True)
    btn.pack(ipady=5, padx=6)
    btn.focus_set()
    about.bind('<Return>', lambda e: about.destroy())
    about.bind('<Escape>', lambda e: about.destroy())

# ================= MANUAL WINDOW =================

def show_manual_window():
    manual_path = os.path.join(base_dir, 'manual.txt')

    manual_win = Toplevel(window)
    manual_win.title('사용설명서')
    manual_win.configure(bg=W_BG)
    manual_win.resizable(True, True)
    width, height = 640, 540
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    manual_win.geometry(f'{width}x{height}+{int(screen_w/2-width/2)}+{int(screen_h/2-height/2)}')
    manual_win.transient(window)

    tbar = Frame(manual_win, bg=W_TITLE_BG, height=38)
    tbar.pack(fill='x', side='top')
    tbar.pack_propagate(False)
    Label(tbar, text='사용설명서', bg=W_TITLE_BG, fg=W_TITLE_FG,
          font=('굴림', 11, 'bold')).pack(side='left', padx=16, pady=8)

    text_frame = Frame(manual_win, bg=W_BG)
    text_frame.pack(fill='both', expand=True, padx=12, pady=10)

    scrollbar = Scrollbar(text_frame)
    scrollbar.pack(side='right', fill='y')

    text_box = Text(text_frame, bg=W_PANEL, fg=W_FG,
                    font=('굴림', 10), wrap='word',
                    yscrollcommand=scrollbar.set, state='normal',
                    bd=1, relief='solid', padx=10, pady=8)
    text_box.pack(side='left', fill='both', expand=True)
    scrollbar.config(command=text_box.yview)

    default_content = (
        f"{APP_NAME} 사용설명서\n"
        "==================================================\n\n"
        "[기본 조작]\n"
        "  방향키 UP / DOWN    : 항목 이동\n"
        "  방향키 LEFT / RIGHT : 좌우 패널 전환\n"
        "  Enter               : 폴더 열기 / 파일 실행\n"
        "  Space               : 파일/폴더 선택 (마크)\n\n"
        "[파일 작업]\n"
        "  Ctrl + C       : 선택 항목 복사\n"
        "  Ctrl + M       : 선택 항목 이동\n"
        "  Ctrl + D       : 선택 항목 삭제\n"
        "  Ctrl + R       : 이름 바꾸기\n"
        "  Ctrl + N       : 새 폴더 만들기\n"
        "  Ctrl + E       : 메모장으로 열기\n"
        "  Ctrl + W       : 탐색기로 현재 폴더 열기\n"
        "  Ctrl + O       : CMD 관리자 권한으로 열기\n"
        "  Ctrl + I       : 시스템 정보\n\n"
        "[기능키]\n"
        "  F1 ~ F12       : 설정된 프로그램 실행\n"
        "  F1 (미설정 시) : 메뉴 열기\n\n"
        "[종료]\n"
        "  Alt + F4       : 프로그램 종료\n\n"
        "[검색]\n"
        "  영문/한글 첫 글자 입력 시 해당 항목으로 이동\n"
        "  한글 초성 입력도 지원 (예: ㅎ → ㅎ으로 시작하는 항목)\n\n"
        "[설정]\n"
        "  설정 메뉴 > 기능키 설정에서 F1~F12에\n"
        "  원하는 프로그램 경로를 등록할 수 있습니다.\n"
        "  설정은 wdir_config.ini 파일에 저장됩니다.\n\n"
        "==================================================\n"
        "이 파일(manual.txt)을 메모장으로 직접 수정하면\n"
        "다음 실행 시 변경된 내용이 반영됩니다.\n"
    )

    if os.path.exists(manual_path):
        try:
            with open(manual_path, 'r', encoding='utf-8') as f:
                text_box.insert('1.0', f.read())
        except:
            text_box.insert('1.0', default_content)
    else:
        text_box.insert('1.0', default_content)
        try:
            with open(manual_path, 'w', encoding='utf-8') as f:
                f.write(default_content)
        except:
            pass
    text_box.config(state='disabled')

    bf = Frame(manual_win, bg=W_BG)
    bf.pack(pady=8)
    w_button(bf, '닫기', manual_win.destroy, primary=False).pack(ipady=5)
    manual_win.bind('<Escape>', lambda e: manual_win.destroy())

# ================= SETTING WINDOW =================

def show_setting_window():
    setting_win = Toplevel(window)
    setting_win.title(f'{APP_NAME} - 기능키 설정')
    setting_win.configure(bg=W_BG)
    setting_win.resizable(False, False)
    width, height = 660, 680   # F12 행 추가로 높이 늘림
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    setting_win.geometry(f'{width}x{height}+{int(screen_w/2-width/2)}+{int(screen_h/2-height/2)}')
    setting_win.transient(window)
    setting_win.grab_set()

    tbar = Frame(setting_win, bg=W_TITLE_BG, height=38)
    tbar.pack(fill='x', side='top')
    tbar.pack_propagate(False)
    Label(tbar, text='기능키 설정  (F1 ~ F12)', bg=W_TITLE_BG, fg=W_TITLE_FG,
          font=('굴림', 11, 'bold')).pack(side='left', padx=16, pady=8)

    hint_frame = Frame(setting_win, bg=W_HOVER, padx=14, pady=6)
    hint_frame.pack(fill='x', padx=16, pady=(10, 0))
    Label(hint_frame, text='※ F1을 비워두면 기본 메뉴(About / Manual / Setting)로 동작합니다.  종료: Alt+F4',
          bg=W_HOVER, fg='#555555', font=('굴림', 9)).pack(anchor='w')

    main_frame = Frame(setting_win, bg=W_BG, padx=16, pady=8)
    main_frame.pack(fill='both', expand=True)

    entries = {}

    def browse_file(key_name):
        file_path = filedialog.askopenfilename(
            parent=setting_win,
            title=f"Select Executable for {key_name}",
            filetypes=[('Executable Files', '*.exe'), ('All Files', '*.*')])
        if file_path:
            entries[key_name].delete(0, END)
            entries[key_name].insert(0, file_path.replace('/', '\\'))

    # F1~F12 모두 기능키로 표시
    for idx, f_key in enumerate([f'F{i}' for i in range(1, 13)]):
        Label(main_frame, text=f_key, bg=W_BG, fg=W_ACCENT,
              font=('굴림', 10, 'bold'), width=5, anchor='w').grid(row=idx, column=0, pady=3, sticky='w')
        entry = Entry(main_frame, bg=W_ENTRY_BG, fg=W_ENTRY_FG,
                      insertbackground=W_FG, relief='solid', bd=1,
                      font=('굴림', 10), width=52)
        entry.grid(row=idx, column=1, padx=5, pady=3)
        entry.insert(0, config.get('KEY_MAPPING', f_key, fallback=''))
        entries[f_key] = entry
        b = Button(main_frame, text='찾아보기', bg=W_BG, fg=W_FG,
                   activebackground=W_HOVER, activeforeground=W_FG,
                   font=('굴림', 9), padx=6, bd=1, relief='solid',
                   cursor='hand2', command=lambda k=f_key: browse_file(k))
        b.grid(row=idx, column=2, padx=5, pady=3)

    Frame(setting_win, bg=W_BORDER, height=1).pack(fill='x', padx=16, pady=(4,0))
    btn_frame = Frame(setting_win, bg=W_BG)
    btn_frame.pack(pady=12)

    def save_settings():
        for f_key in entries:
            config['KEY_MAPPING'][f_key] = entries[f_key].get().strip()
        with open(INI_FILE, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        update_topbar_labels()
        setting_win.destroy()

    w_button(btn_frame, '저장', save_settings, primary=True).pack(side='left', padx=6, ipady=5)
    w_button(btn_frame, '취소', setting_win.destroy, primary=False).pack(side='left', padx=6, ipady=5)

# ================= FILE OPERATIONS =================

def toggle_space_mark(event):
    if menu_mode or active is None: return 'break'
    sel = active.curselection()
    if not sel: return 'break'
    idx = sel[0]
    if active == left_lb:
        if left_types[idx] not in ['DIR', 'FILE'] or left_lb.get(idx).endswith('[..] UP'): return 'break'
        if idx in left_marked:
            left_marked.remove(idx)
            left_lb.itemconfig(idx, fg=COLOR_DIR if left_types[idx]=='DIR' else COLOR_FILE)
        else:
            left_marked.add(idx)
            left_lb.itemconfig(idx, fg=COLOR_MARKED)
    else:
        if right_types[idx] not in ['DIR', 'FILE']: return 'break'
        if idx in right_marked:
            right_marked.remove(idx)
            right_lb.itemconfig(idx, fg=COLOR_DIR if right_types[idx]=='DIR' else COLOR_FILE)
        else:
            right_marked.add(idx)
            right_lb.itemconfig(idx, fg=COLOR_MARKED)
    next_idx = idx + 1
    if active == left_lb:
        if next_idx < left_lb.size(): set_active_left(next_idx)
    else:
        if next_idx < right_lb.size(): set_active_right(next_idx)
    return 'break'

def get_target_paths():
    targets = []
    if active == left_lb:
        if left_marked:
            for idx in left_marked: targets.append(left_items[idx])
        else:
            sel = left_lb.curselection()
            if sel and left_types[sel[0]] in ['DIR','FILE'] and not left_lb.get(sel[0]).endswith('[..] UP'):
                targets.append(left_items[sel[0]])
    else:
        if right_marked:
            for idx in right_marked: targets.append(right_items[idx])
        else:
            sel = right_lb.curselection()
            if sel and right_types[sel[0]] in ['DIR','FILE']:
                targets.append(right_items[sel[0]])
    return targets

def copy_items(event=None):
    targets = get_target_paths()
    if not targets: return 'break'
    dest = filedialog.askdirectory(title="복사 목적지 선택", initialdir=current_path)
    if not dest: return 'break'
    for t in targets:
        if not os.path.exists(t): continue
        d_path = os.path.join(dest, os.path.basename(t))
        if os.path.abspath(t).lower() == os.path.abspath(d_path).lower(): continue
        try:
            if os.path.isdir(t): shutil.copytree(t, d_path, dirs_exist_ok=True)
            else: shutil.copy2(t, d_path)
        except Exception as e: messagebox.showerror("Error", str(e))
    load(current_path, keep_focus=True)
    return 'break'

def move_items(event=None):
    targets = get_target_paths()
    if not targets: return 'break'
    dest = filedialog.askdirectory(title="이동 목적지 선택", initialdir=current_path)
    if not dest: return 'break'
    for t in targets:
        if not os.path.exists(t): continue
        d_path = os.path.join(dest, os.path.basename(t))
        if os.path.abspath(t).lower() == os.path.abspath(d_path).lower(): continue
        try: shutil.move(t, d_path)
        except Exception as e: messagebox.showerror("Error", str(e))
    load(current_path, keep_focus=True)
    return 'break'

def delete_items(event=None):
    targets = get_target_paths()
    if not targets: return 'break'
    if messagebox.askyesno("삭제", f"선택한 {len(targets)}개 항목을 정말 삭제하시겠습니까?"):
        for t in targets:
            if not os.path.exists(t): continue
            try:
                if os.path.isdir(t): shutil.rmtree(t)
                else: os.remove(t)
            except Exception as e: messagebox.showerror("Error", str(e))
        load(current_path, keep_focus=True)
    return 'break'

# ================= RENAME =================

def rename_item(event=None):
    if menu_mode: return 'break'
    target = get_selection()
    if not target or not os.path.exists(target): return 'break'
    old_name = os.path.basename(target)

    win, body = make_dialog('이름 바꾸기', width=460, height=200)

    Label(body, text='새 이름:', bg=W_BG, fg=W_FG,
          font=('굴림', 10)).pack(anchor='w', pady=(0,4))
    entry = w_entry(body, width=48)
    entry.pack(pady=(0,2), fill='x')
    entry.insert(0, old_name)
    if os.path.isfile(target):
        entry.selection_range(0, len(os.path.splitext(old_name)[0]))
    else:
        entry.selection_range(0, END)
    entry.focus_set()

    def confirm():
        new_name = entry.get().strip()
        if not new_name or new_name == old_name: win.destroy(); return
        new_path = os.path.join(os.path.dirname(target), new_name)
        if os.path.exists(new_path):
            messagebox.showerror('오류', '같은 이름이 이미 존재합니다.', parent=win); return
        try:
            os.rename(target, new_path)
            win.destroy()
            load(current_path, keep_focus=True)
        except Exception as e:
            messagebox.showerror('오류', f'이름 변경 실패:\n{str(e)}', parent=win)

    bf = Frame(body, bg=W_BG)
    bf.pack(pady=10, anchor='e')
    w_button(bf, '확인', confirm, primary=True).pack(side='left', padx=4, ipady=5)
    w_button(bf, '취소', win.destroy, primary=False).pack(side='left', padx=4, ipady=5)
    win.bind('<Return>', lambda e: confirm())
    win.bind('<Escape>', lambda e: win.destroy())
    return 'break'

# ================= MAKE DIRECTORY =================

def make_directory(event=None):
    if menu_mode: return 'break'

    win, body = make_dialog('새 폴더 만들기', width=460, height=200)

    Label(body, text='폴더 이름:', bg=W_BG, fg=W_FG,
          font=('굴림', 10)).pack(anchor='w', pady=(0,4))
    entry = w_entry(body, width=48)
    entry.pack(pady=(0,2), fill='x')
    entry.focus_set()

    def confirm():
        dir_name = entry.get().strip()
        if not dir_name: win.destroy(); return
        new_dir_path = os.path.join(current_path, dir_name)
        if os.path.exists(new_dir_path):
            messagebox.showerror('오류', '이미 존재하는 폴더명입니다.', parent=win); return
        try:
            os.makedirs(new_dir_path)
            win.destroy()
            load(current_path, keep_focus=True)
        except Exception as e:
            messagebox.showerror('오류', f'폴더 생성 실패:\n{str(e)}', parent=win)

    bf = Frame(body, bg=W_BG)
    bf.pack(pady=10, anchor='e')
    w_button(bf, '만들기', confirm, primary=True).pack(side='left', padx=4, ipady=5)
    w_button(bf, '취소', win.destroy, primary=False).pack(side='left', padx=4, ipady=5)
    win.bind('<Return>', lambda e: confirm())
    win.bind('<Escape>', lambda e: win.destroy())
    return 'break'

# ================= SELECTION =================

def get_selection():
    if active is None: return None
    sel = active.curselection()
    if not sel: return None
    i = sel[0]
    if active == left_lb:
        return left_items[i] if i < len(left_items) else None
    else:
        return right_items[i] if i < len(right_items) else None

def open_with_notepad_click(event=None):
    target = get_selection()
    if not target or target == '': return
    if os.path.isfile(target):
        try: subprocess.Popen(['notepad.exe', target])
        except: pass

# ================= OPEN EXPLORER =================

def open_explorer_here(event=None):
    try:
        subprocess.Popen(f'explorer.exe "{current_path}"', shell=True)
    except Exception as e:
        messagebox.showerror("Error", str(e))
    return 'break'

# ================= SYSTEM INFO =================

def show_sysinfo_window(event=None):
    import ctypes as _ctypes
    import socket

    os_info = f"{platform.system()} {platform.release()}  (빌드: {platform.version()})"

    cpu_name = "Unknown"
    core_count = ""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        winreg.CloseKey(key)
    except: pass
    try:
        import multiprocessing
        core_count = f"논리 프로세서: {multiprocessing.cpu_count()}개"
    except: pass

    ram_info = "Unknown"
    try:
        class MEMORYSTATUSEX(_ctypes.Structure):
            _fields_ = [
                ("dwLength", _ctypes.c_ulong),
                ("dwMemoryLoad", _ctypes.c_ulong),
                ("ullTotalPhys", _ctypes.c_ulonglong),
                ("ullAvailPhys", _ctypes.c_ulonglong),
                ("ullTotalPageFile", _ctypes.c_ulonglong),
                ("ullAvailPageFile", _ctypes.c_ulonglong),
                ("ullTotalVirtual", _ctypes.c_ulonglong),
                ("ullAvailVirtual", _ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", _ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = _ctypes.sizeof(stat)
        _ctypes.windll.kernel32.GlobalMemoryStatusEx(_ctypes.byref(stat))
        total_gb = stat.ullTotalPhys / 1024**3
        avail_gb = stat.ullAvailPhys / 1024**3
        used_gb  = total_gb - avail_gb
        ram_info = f"{total_gb:.1f} GB  (사용: {used_gb:.1f} GB / 여유: {avail_gb:.1f} GB / {stat.dwMemoryLoad}%)"
    except: pass

    def fmt(b):
        return f"{b/1024**4:.2f} TB" if b >= 1024**4 else f"{b/1024**3:.1f} GB"
    drive_lines = []
    for d in _drives:
        try:
            total, used, free = shutil.disk_usage(d)
            drive_lines.append((d[0], fmt(total), fmt(used), fmt(free)))
        except:
            drive_lines.append((d[0], '-', '-', '-'))

    hostname = ''
    local_ip = ''
    extra_ips = []
    try:
        hostname = socket.gethostname()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
        except:
            local_ip = '연결 없음'
        finally:
            s.close()
        seen = {local_ip, '127.0.0.1'}
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ':' not in ip and ip not in seen:
                extra_ips.append(ip)
                seen.add(ip)
    except Exception as e:
        hostname = f'오류: {e}'

    net_rows = 2 + len(extra_ips)
    base_height = 540
    extra_height = max(0, net_rows - 2) * 22
    win_height = base_height + extra_height

    info_win = Toplevel(window)
    info_win.title('시스템 정보')
    info_win.configure(bg=W_BG)
    info_win.resizable(False, False)
    width = 620
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    info_win.geometry(f'{width}x{win_height}+{int(screen_w/2-width/2)}+{int(screen_h/2-win_height/2)}')
    info_win.transient(window)
    info_win.grab_set()

    tbar = Frame(info_win, bg=W_TITLE_BG, height=38)
    tbar.pack(fill='x', side='top')
    tbar.pack_propagate(False)
    Label(tbar, text='시스템 정보', bg=W_TITLE_BG, fg=W_TITLE_FG,
          font=('굴림', 11, 'bold')).pack(side='left', padx=16, pady=8)

    body = Frame(info_win, bg=W_BG, padx=20, pady=12)
    body.pack(fill='both', expand=True)

    def section(title):
        f = Frame(body, bg=W_BG)
        f.pack(fill='x', pady=(10, 4))
        Label(f, text=title, bg=W_BG, fg=W_ACCENT,
              font=('굴림', 10, 'bold')).pack(side='left')
        Frame(body, bg=W_BORDER, height=1).pack(fill='x')

    def row(label, value):
        f = Frame(body, bg=W_BG)
        f.pack(fill='x', padx=8, pady=2)
        Label(f, text=label, bg=W_BG, fg='#666666',
              font=('굴림', 9), width=12, anchor='w').pack(side='left')
        Label(f, text=value, bg=W_BG, fg=W_FG,
              font=('굴림', 10), anchor='w').pack(side='left')

    section('운영체제')
    row('OS', os_info)

    section('CPU')
    row('모델', cpu_name)
    if core_count: row('코어', core_count)

    section('메모리 (RAM)')
    row('용량', ram_info)

    section('드라이브')
    for drv, total, used, free in drive_lines:
        row(f'[{drv}:]', f'전체 {total}  /  사용 {used}  /  여유 {free}')

    section('네트워크')
    row('호스트명', hostname if hostname else '알 수 없음')
    row('로컬 IP', local_ip if local_ip else '알 수 없음')
    for ip in extra_ips:
        row('추가 IP', ip)

    Frame(info_win, bg=W_BORDER, height=1).pack(fill='x', padx=16)
    bf = Frame(info_win, bg=W_BG)
    bf.pack(pady=10)
    btn = w_button(bf, '닫기', info_win.destroy, primary=True)
    btn.pack(ipady=5, padx=6)
    btn.focus_set()
    info_win.bind('<Escape>', lambda e: info_win.destroy())
    info_win.bind('<Return>', lambda e: info_win.destroy())
    return 'break'

# ================= EXECUTE =================

def execute_custom_key(f_key):
    cmd_path = config.get('KEY_MAPPING', f_key, fallback='').strip()
    if not cmd_path:
        if f_key == 'F1': toggle_f1_menu()
        return
    if "cmd.exe" in cmd_path.lower(): open_cmd_admin()
    elif "powershell.exe" in cmd_path.lower(): open_powershell_admin()
    else:
        try:
            if os.path.isabs(cmd_path): subprocess.Popen([cmd_path], cwd=current_path)
            else: subprocess.Popen(cmd_path, shell=True, cwd=current_path)
        except: pass

def open_cmd_admin():
    try: ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f'/k cd /d "{current_path}"', None, 1)
    except: pass

def open_powershell_admin():
    try: ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", f'-NoExit -Command "Set-Location \'{current_path}\'"', None, 1)
    except: pass

def open_cmd_here(event=None):
    if menu_mode: return
    open_cmd_admin()
    return 'break'

# ================= F1 MENU =================

def close_f1_menu():
    global f1_menu, menu_mode
    menu_mode = False
    if f1_menu: f1_menu.destroy(); f1_menu = None
    if active == right_lb: right_lb.focus_set()
    else: left_lb.focus_set()

def update_menu_select():
    for i, lbl in enumerate(menu_labels):
        if i == menu_index: lbl.config(bg=W_ACCENT, fg=W_ACCENT_FG)
        else: lbl.config(bg=W_PANEL, fg=W_FG)

def menu_up():
    global menu_index
    if menu_index > 0: menu_index -= 1
    update_menu_select()

def menu_down():
    global menu_index
    if menu_index < len(menu_labels)-1: menu_index += 1
    update_menu_select()

def menu_enter_by_text(text):
    if text.startswith('About'): show_about_window()
    elif text.startswith('Manual'): show_manual_window()
    elif text.startswith('Setting'): show_setting_window()
    close_f1_menu()

def menu_enter():
    menu_enter_by_text(menu_labels[menu_index]['text'])

def toggle_f1_menu(event=None):
    global f1_menu, menu_mode, menu_index, menu_labels
    if f1_menu: close_f1_menu(); return 'break'
    menu_mode = True; menu_index = 0; menu_labels.clear()
    f1_menu = Frame(window, bg=W_PANEL,
                    highlightbackground=W_BORDER, highlightthickness=1)
    f1_menu.place(x=5, y=28)
    for item in ['About (A)', 'Manual (M)', 'Setting (S)']:
        lbl = Label(f1_menu, text=item, bg=W_PANEL, fg=W_FG, anchor='w',
                    width=20, padx=12, pady=5, font=('굴림', 10), cursor='hand2')
        lbl.pack(fill='x')
        lbl.bind('<Button-1>', lambda e, t=item: menu_enter_by_text(t))
        menu_labels.append(lbl)
    update_menu_select()
    return 'break'

def menu_shortcut(event):
    if not menu_mode: return
    key = event.keysym.lower()
    if key == 'a': show_about_window(); close_f1_menu()
    elif key == 'm': show_manual_window(); close_f1_menu()
    elif key == 's': show_setting_window(); close_f1_menu()

# ================= FUNCTION BAR =================

def function_click(name):
    pure_key = name.split()[0] if ' ' in name else name
    # F1~F12 모두 기능키 실행 (종료 없음 - Alt+F4 사용)
    if pure_key in [f'F{i}' for i in range(1, 13)]:
        execute_custom_key(pure_key)

def update_topbar_labels():
    for key in function_keys:
        pk = key.split()[0]
        mp = config.get('KEY_MAPPING', pk, fallback='').strip()
        if mp:
            txt = f'{pk} {os.path.splitext(os.path.basename(mp).upper())[0]}'
        elif pk == 'F1':
            txt = 'F1 MENU'
        else:
            txt = pk
        if pk in topbar_labels:
            topbar_labels[pk].config(text=txt)

for key in function_keys:
    pk = key.split()[0]
    lbl = Label(topbar, text=key, bg='navy', fg='white',
                font=('굴림', 10, 'bold'), padx=10, pady=4, cursor='hand2')
    lbl.pack(side='left')
    lbl.bind('<Button-1>', lambda e, k=key: function_click(k))
    topbar_labels[pk] = lbl

update_topbar_labels()

# ================= LOAD =================

def load(path, keep_focus=False):
    global current_path, current_dir_count, current_file_count
    prev_active = active
    prev_idx = 0
    if prev_active:
        sel = prev_active.curselection()
        if sel: prev_idx = sel[0]
    left_lb.delete(0, END); right_lb.delete(0, END)
    left_items.clear(); right_items.clear()
    left_types.clear(); right_types.clear()
    left_marked.clear(); right_marked.clear()
    current_path = path
    parent = os.path.dirname(path.rstrip('\\'))
    if parent and parent != path: insert_left('[..]', parent, 'DIR')
    try: items = os.listdir(path)
    except: items = []
    folders, files = [], []
    for i in items:
        full = os.path.join(path, i)
        if os.path.isdir(full): folders.append((i, full))
        else: files.append((i, full))
    folders.sort(); files.sort()
    current_dir_count = len(folders); current_file_count = len(files)
    for n, f in folders: insert_left('[DIR] ' + n, f, 'DIR')
    for n, f in files: insert_right('' + n, f, 'FILE')
    for d in _drives: insert_right(f'[-{d[0]}:-]', d, 'DRIVE')
    if keep_focus and prev_active:
        if prev_active == right_lb: set_active_right(prev_idx)
        else: set_active_left(prev_idx)
    else: set_active_left(0)
    update_footer()

# ================= OPEN =================

def open_item():
    t = get_selection()
    if not t or t == '': return
    if t in _drives: load(t); return
    if os.path.isdir(t): load(t)
    else:
        try:
            if os.path.splitext(t)[1].lower() in run_ext:
                subprocess.Popen(t, shell=True)
        except: pass

# ================= ACTIVE =================

def set_active_left(idx=0):
    global active
    active = left_lb; left_lb.focus_set(); right_lb.selection_clear(0, END)
    if left_lb.size() > 0:
        idx = min(idx, left_lb.size()-1)
        left_lb.selection_clear(0, END); left_lb.selection_set(idx)
        left_lb.activate(idx); left_lb.see(idx)

def set_active_right(idx=0):
    global active
    active = right_lb; right_lb.focus_set(); left_lb.selection_clear(0, END)
    if right_lb.size() > 0:
        idx = min(idx, right_lb.size()-1)
        right_lb.selection_clear(0, END); right_lb.selection_set(idx)
        right_lb.activate(idx); right_lb.see(idx)

# ================= MOVE =================

def move_left(event):
    if menu_mode: return 'break'
    idx = left_lb.curselection()
    set_active_left(idx[0] if idx else 0); return 'break'

def move_right(event):
    if menu_mode: return 'break'
    idx = right_lb.curselection()
    set_active_right(idx[0] if idx else 0); return 'break'

# ================= KEY =================

def key_up(event):
    if menu_mode: menu_up(); return 'break'
    return None

def key_down(event):
    if menu_mode: menu_down(); return 'break'
    return None

def key_enter(event):
    if menu_mode: menu_enter(); return 'break'
    open_item(); return 'break'

def get_chosung(char):
    if not char: return ''
    code = ord(char)
    if 0xAC00 <= code <= 0xD7A3:
        cl = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
        return cl[(code - 0xAC00) // 588]
    return char

def handle_character_press(event):
    if menu_mode or active is None: return None
    char = event.char
    if not char or char in [' ', '\r', '\x1b']: return None
    char_lower = char.lower()
    size = active.size()
    if size == 0: return None
    current_sel = active.curselection()
    start_idx = current_sel[0] if current_sel else 0
    input_chosung = get_chosung(char_lower)
    for i in range(1, size + 1):
        test_idx = (start_idx + i) % size
        item_text = active.get(test_idx)
        pure_name = item_text
        if item_text.startswith('[DIR] '): pure_name = item_text[6:]
        elif item_text.startswith('[FILE] '): pure_name = item_text[7:]
        elif item_text.startswith('[-') and item_text.endswith(':-]'): pure_name = item_text[2:3]
        if pure_name:
            target_first_char = pure_name[0].lower()
            target_chosung = get_chosung(target_first_char)
            if target_first_char == char_lower or target_chosung == input_chosung:
                if active == left_lb: set_active_left(test_idx)
                else: set_active_right(test_idx)
                return 'break'
    return None

# ================= BIND =================

# F1~F12 모두 기능키로 바인딩
for i in range(1, 13):
    window.bind(f'<F{i}>', lambda e, i=i: function_click(f'F{i}'))

window.bind_all('<Up>', key_up)
window.bind_all('<Down>', key_down)
window.bind_all('<Return>', key_enter)
window.bind_all('<Key>', menu_shortcut)
window.bind('<Left>', move_left)
window.bind('<Right>', move_right)

window.bind_all('<space>', toggle_space_mark)
window.bind_all('<Control-c>', copy_items)
window.bind_all('<Control-m>', move_items)
window.bind_all('<Control-d>', delete_items)
window.bind_all('<Control-r>', rename_item)
window.bind_all('<Control-n>', make_directory)
window.bind_all('<Control-e>', open_with_notepad_click)
window.bind_all('<Control-w>', open_explorer_here)
window.bind_all('<Control-o>', open_cmd_here)
window.bind_all('<Control-i>', show_sysinfo_window)

def on_double_click(event):
    open_item(); return 'break'

left_lb.bind('<Button-1>', lambda e: set_active_left(left_lb.nearest(e.y)))
right_lb.bind('<Button-1>', lambda e: set_active_right(right_lb.nearest(e.y)))
left_lb.bind('<Double-Button-1>', on_double_click)
right_lb.bind('<Double-Button-1>', on_double_click)

left_lb.bind('<FocusIn>', lambda e: set_active_left(left_lb.curselection()[0] if left_lb.curselection() else 0))
right_lb.bind('<FocusIn>', lambda e: set_active_right(right_lb.curselection()[0] if right_lb.curselection() else 0))

left_lb.bind('<Key>', handle_character_press)
right_lb.bind('<Key>', handle_character_press)

# ================= START =================

load(_drives[0])
update_footer()
update_clock()

window.mainloop()
