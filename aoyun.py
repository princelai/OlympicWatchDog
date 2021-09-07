from datetime import date

import httpx
import urwid
from prettytable import PrettyTable


def get_score(name, mid):
    req = httpx.get("https://app.sports.qq.com/TokyoOly/statDetail", params={"mid": mid})
    try:
        data = req.json()['data']['stats'][0]['rows']
    except (KeyError, IndexError):
        return '暂无比分'
    except Exception as e:
        return e

    result = []
    for row in data:
        result.append([col['html'] for col in row])
    correct_num = len(result[0])
    result = list(filter(lambda x: len(x) == correct_num, result))

    result[0][0] = name
    t = PrettyTable(result[0])
    t.add_rows(result[1:])
    # print(t)
    # print(tabulate(result[1:], headers=result[0]))
    return t


class Match:
    def __init__(self, data_dict: dict):
        self.match_name = data_dict['matchDesc']
        self.start_time = data_dict['startTime']
        self.is_china = bool(data_dict['isChina']) and eval(data_dict['isChina'])
        self.is_gold = bool(data_dict['isGold']) and eval(data_dict['isGold'])
        self.mid = data_dict['mid']
        self.quarter = data_dict['quarter']
        self.live_period = int(data_dict['livePeriod'])
        self.has_score = self.live_period >= 1

    def __repr__(self):
        extra_info = [self.quarter]
        if self.is_gold:
            extra_info.append('(金牌)')
        if self.is_china:
            extra_info.append('(中国队)')
        return f"{self.match_name}  {self.start_time}  {''.join(extra_info)}"

    def __str__(self):
        return self.__repr__()


class MatchList:
    my_match = []

    @classmethod
    def update(cls, *args):
        dt = str(date.today())
        # dt = "2021-07-29"
        req = httpx.get(f"https://app.sports.qq.com/match/list?columnId=130003&dateNum=1&flag=2&date={dt}&parentChildType=1")
        match_list = req.json()['data']['matches'][dt]['list']

        for i, match in enumerate(match_list):
            if int(match['categoryId']) > 3:
                # livePeriod 0:未开始,1:进行中,2:已结束
                # liveType 1:图文,4:视频
                d = {"matchDesc": match['matchInfo']['matchDesc'], "startTime": match['matchInfo']['startTime'],
                     "isChina": match['matchInfo'].get('isChina', 0), "isGold": match['matchInfo'].get('isGold', 0), "mid": match['matchInfo']['mid'],
                     "quarter": match['matchInfo'].get('quarter', 0), "livePeriod": match['matchInfo'].get('livePeriod', 0)}
                cls.my_match.append(Match(d))

    @classmethod
    def filter_china(cls, iter_match=None):
        if iter_match is None:
            return filter(lambda x: x.is_china == 1, cls.my_match)
        else:
            return filter(lambda x: x.is_china == 1, iter_match)

    @classmethod
    def filter_ing(cls, iter_match=None):
        if iter_match is None:
            return filter(lambda x: x.live_period == 1, cls.my_match)
        else:
            return filter(lambda x: x.live_period == 1, iter_match)

    @classmethod
    def filter_end(cls, iter_match=None):
        if iter_match is None:
            return filter(lambda x: x.live_period == 2, cls.my_match)
        else:
            return filter(lambda x: x.live_period == 2, iter_match)

    @classmethod
    def filter_not_begin(cls, iter_match=None):
        if iter_match is None:
            return filter(lambda x: x.live_period == 0, cls.my_match)
        else:
            return filter(lambda x: x.live_period == 0, iter_match)

    @classmethod
    def filter_gold(cls, iter_match=None):
        if iter_match is None:
            return filter(lambda x: x.is_gold == 1, cls.my_match)
        else:
            return filter(lambda x: x.is_gold == 1, iter_match)

    @classmethod
    def filter_has_score(cls, iter_match=None):
        if iter_match is None:
            return filter(lambda x: x.has_score == 1, cls.my_match)
        else:
            return filter(lambda x: x.has_score == 1, iter_match)


def menu_button(caption, callback):
    button = urwid.Button(str(caption))
    urwid.connect_signal(button, 'click', callback, caption)
    return urwid.AttrMap(button, None, focus_map='reversed')


def sub_menu(caption, choices):
    contents = menu(caption, choices)

    def open_menu(button, *args):
        return top.open_box(contents)

    return menu_button(str(caption), open_menu)


def menu(title, choices):
    body = [urwid.Text(title), urwid.Divider()]
    body.extend(choices)
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))


def generate_menu():
    menu_top = menu(u'主目录', [
        sub_menu('正在进行', [menu_button(m, item_chosen) for m in MatchList.filter_ing()]),
        sub_menu('今日决赛', [menu_button(m, item_chosen) for m in MatchList.filter_gold()]),
        sub_menu('中国队', [menu_button(m, item_chosen) for m in MatchList.filter_china()]),
        sub_menu('即将开始', [urwid.Text(str(m)) for m in MatchList.filter_not_begin()]),
        menu_button('刷新数据(F5)', MatchList.update),
        menu_button('退出', exit_program)
    ])
    return menu_top


def item_chosen(button, obj):
    response = urwid.Text(str(get_score(obj.match_name, obj.mid)))
    done = menu_button('返回', return_back)
    top.open_box(urwid.Filler(urwid.Pile([response, done])))


def return_back(button, *args):
    top.keypress(None, 'esc')


def exit_program(button, *args):
    raise urwid.ExitMainLoop()


class CascadingBoxes(urwid.WidgetPlaceholder):
    max_box_levels = 3

    def __init__(self, box):
        super(CascadingBoxes, self).__init__(urwid.SolidFill('\N{MEDIUM SHADE}'))
        self.box_level = 0
        self.open_box(box)

    def open_box(self, box):
        self.original_widget = urwid.Overlay(urwid.LineBox(box),
                                             self.original_widget,
                                             align=('relative', 10), width=('relative', 90),
                                             valign=('relative', 10), height=('relative', 90),
                                             min_width=32, min_height=16,
                                             left=self.box_level * 3,
                                             right=(self.max_box_levels - self.box_level - 1) * 3,
                                             top=self.box_level * 2,
                                             bottom=(self.max_box_levels - self.box_level - 1) * 2)
        self.box_level += 1

    def keypress(self, size, key):
        if key == 'esc' and self.box_level > 1:
            self.original_widget = self.original_widget[0]
            self.box_level -= 1
        elif key == 'f5':
            generate_menu()
            MatchList.update()
            while self.box_level > 1:
                self.original_widget = self.original_widget[0]
                self.box_level -= 1
        else:
            return super(CascadingBoxes, self).keypress(size, key)


if __name__ == "__main__":
    MatchList.update()

    top = CascadingBoxes(generate_menu())
    try:
        urwid.MainLoop(top, palette=[('reversed', 'standout', '')]).run()
    except KeyboardInterrupt:
        print("bye bye!")
        exit(1)
