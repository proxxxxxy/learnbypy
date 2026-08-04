# -*- coding: utf-8 -*-
#
#  Flash-Card Viewer (Pythonista 3)                2025-06-02
#  • JSON (list*.json) を読み込みカード表示
#  • 文字量でフォント自動縮小
#  • 複数行回答は数字だけ左端揃え、全体は中央寄せ
# --------------------------------------------------------------------

import ui, random, console, json, os, re

# ──────────────────────────────────────────
#  JSON 読み込み
# ──────────────────────────────────────────
def load_word_list():
    files = [f for f in os.listdir() if f.startswith('list') and f.endswith('.json')]
    if not files:
        console.alert('エラー', 'list*.json ファイルが見つかりません', '終了')
        return []
    if len(files) == 1:
        filename = files[0]
    else:
        idx = console.alert('単語リスト選択', '', *files)
        filename = files[idx - 1]
    with open(filename, encoding='utf-8') as f:
        return json.load(f)

WORDS = load_word_list()
if not WORDS:
    exit()

# ──────────────────────────────────────────
#  メインビュー
# ──────────────────────────────────────────
class CardView(ui.View):
    BTN_H = 64

    def __init__(self, cards, shuffle_first):
        super().__init__(bg_color='white')
        self.all_cards = cards[:]
        self.cards = random.sample(cards, len(cards)) if shuffle_first else cards[:]

        self.index = self.correct = self.attempts = 0
        self.history = []
        self.wrong_cards = []
        self.show_mean = False
        self.jp_first = False  # ここでは英→日固定

        # ラベル
        self.word_lbl = ui.Label(font=('AvenirNext-Bold', 40),
                                 alignment=ui.ALIGN_CENTER,
                                 line_break_mode=ui.LB_WORD_WRAP,
                                 number_of_lines=0)
        self.mean_lbl = ui.Label(font=('AvenirNext-Regular', 30),
                                 alignment=ui.ALIGN_CENTER,
                                 text_color='#555',
                                 line_break_mode=ui.LB_WORD_WRAP,
                                 number_of_lines=0)
        self.stat_lbl = ui.Label(font=('AvenirNext-Regular', 14),
                                 alignment=ui.ALIGN_CENTER,
                                 text_color='#666')

        # ボタン
        self.btn_correct = self._mk_btn('✔︎', '#43a047', self.mark_correct)
        self.btn_wrong   = self._mk_btn('✘', '#e53935', self.mark_wrong)
        self.btn_back    = self._mk_btn('↩︎', '#607d8b', self.go_back)

        self.menu_btn = ui.Button(title='☰', font=('HelveticaNeue', 34),
                                  bg_color=(0.9, 0.9, 0.9, 0.75),
                                  tint_color='black',
                                  action=lambda s: ui.delay(self.menu_dialog, 0.01))
        self.menu_btn.width = self.menu_btn.height = 64
        self.menu_btn.corner_radius = 32

        self.exit_btn = ui.Button(title='✕', font=('HelveticaNeue', 34),
                                  bg_color=(0.9, 0.3, 0.3, 0.75),
                                  tint_color='white',
                                  action=lambda s: self.close())
        self.exit_btn.width = self.exit_btn.height = 64
        self.exit_btn.corner_radius = 32

        for v in (self.word_lbl, self.mean_lbl, self.stat_lbl,
                  self.btn_correct, self.btn_wrong, self.btn_back,
                  self.menu_btn, self.exit_btn):
            self.add_subview(v)

        self.present_card()

    # ───────────────────────────────────────
    #  レイアウト
    # ───────────────────────────────────────
    def layout(self):
        W, H, pad = self.width, self.height, 20
        self.word_lbl.frame = (pad, H * 0.14, W - 2 * pad, 150)
        self.mean_lbl.frame = (pad, H * 0.44, W - 2 * pad, 150)
        self.stat_lbl.frame = (pad, H - 38, W - 2 * pad, 18)

        btn_w = (W - 4 * pad) / 3
        yb = H * 0.75
        self.btn_correct.frame = (pad, yb, btn_w, self.BTN_H)
        self.btn_wrong.frame   = (2 * pad + btn_w, yb, btn_w, self.BTN_H)
        self.btn_back.frame    = (3 * pad + 2 * btn_w, yb, btn_w, self.BTN_H)

        self.menu_btn.x = W - self.menu_btn.width - 14
        self.menu_btn.y = 14
        self.exit_btn.x = self.menu_btn.x - self.exit_btn.width - 10
        self.exit_btn.y = 14

        self._fit_font(self.word_lbl, 40, 14)
        self._fit_font(self.mean_lbl, 30, 12)

    # ───────────────────────────────────────
    #  カード表示
    # ───────────────────────────────────────
    def present_card(self):
        no, eng, jp = self.cards[self.index]
        front, back = (jp, f'{no}. {eng}') if self.jp_first else (f'{no}. {eng}', jp)

        # セット
        self.word_lbl.text = front
        self.mean_lbl.text = back if self.show_mean else '(タップで裏面表示)'
        self.mean_lbl.alpha = 1.0 if self.show_mean else 0.25
        self.stat_lbl.text = f'{self.index+1}/{len(self.cards)}   正解 {self.correct}/{self.attempts}'

        # 2 番号ぶん左寄せパディング(改行のみ対象)
        if self.show_mean and "\n" in self.mean_lbl.text:
            pad = ' ' * 3              # EM SPACE ×3
            new_lines = []
            for ln in self.mean_lbl.text.split('\n'):
                if re.match(r'^\(\d+\)', ln.strip()):
                    new_lines.append(pad + ln.strip())
                else:
                    new_lines.append(ln)
            self.mean_lbl.text = '\n'.join(new_lines)

        self._fit_font(self.word_lbl, 40, 14)
        self._fit_font(self.mean_lbl, 30, 12)

    # ───────────────────────────────────────
    #  フォント自動縮小
    # ───────────────────────────────────────
    def _fit_font(self, label: ui.Label, max_pt: int, min_pt: int = 12):
        base_name, _ = label.font
        max_w, max_h = label.width, label.height
        size = max_pt
        while size >= min_pt:
            label.font = (base_name, size)
            w, h = ui.measure_string(label.text, font=label.font)
            lines = int((w - 1) / max_w) + 1
            if h * lines <= max_h:
                break
            size -= 2
        label.font = (base_name, size)

    # ───────────────────────────────────────
    #  ボタン生成
    # ───────────────────────────────────────
    def _mk_btn(self, title, color, act):
        return ui.Button(title=title, font=('AvenirNext-Bold', 34),
                         bg_color=color, tint_color='white',
                         corner_radius=8, action=act)

    # ───────────────────────────────────────
    #  ボタンアクション
    # ───────────────────────────────────────
    def mark_correct(self, _):
        self.history.append((self.cards[self.index], True))
        self.correct += 1
        self.attempts += 1
        self.next_card()

    def mark_wrong(self, _):
        card = self.cards[self.index]
        self.history.append((card, False))
        self.wrong_cards.append(card)
        self.attempts += 1
        self.next_card()

    def go_back(self, _):
        if not self.history:
            return
        card, ok = self.history.pop()
        self.index = max(0, self.index - 1)
        if ok:
            self.correct -= 1
        else:
            if self.wrong_cards and self.wrong_cards[-1] == card:
                self.wrong_cards.pop()
        self.attempts -= 1
        self.show_mean = False
        self.present_card()

    # ───────────────────────────────────────
    #  進行管理
    # ───────────────────────────────────────
    def next_card(self):
        self.show_mean = False
        self.index += 1
        if self.index >= len(self.cards):
            self.finish_dialog()
        else:
            self.present_card()

    def finish_dialog(self):
        def _after():
            ch = console.alert('完了', f'正解 {self.correct}/{self.attempts}',
                               '全部やり直す', '不正解だけ', '終了')
            if ch == 1:
                self.order_dialog(self.all_cards)
            elif ch == 2:
                self.order_dialog(self.wrong_cards if self.wrong_cards else self.all_cards)
            else:
                self.close()
        ui.delay(_after, 0.02)

    def order_dialog(self, new_cards):
        if not new_cards:
            console.alert('不正解はありません', '', 'OK')
            new_cards = self.all_cards
        ch = console.alert('順序選択', '', '順番', 'ランダム')
        self.reset_with(new_cards, shuffle=(ch == 2))

    def reset_with(self, clist, shuffle):
        self.cards = random.sample(clist, len(clist)) if shuffle else clist[:]
        self.index = self.correct = self.attempts = 0
        self.history.clear()
        self.wrong_cards.clear()
        self.show_mean = False
        self.present_card()

    # ───────────────────────────────────────
    #  メニュー
    # ───────────────────────────────────────
    def menu_dialog(self):
        ch = console.alert('メニュー', '',
                           '順番で最初から', 'シャッフルで最初から',
                           '表示方向を切替', 'キャンセル')
        if ch == 1:
            self.reset_with(self.all_cards, shuffle=False)
        elif ch == 2:
            self.reset_with(self.all_cards, shuffle=True)
        elif ch == 3:
            self.jp_first = not self.jp_first
            self.present_card()

    # ───────────────────────────────────────
    #  タップで裏表切り替え
    # ───────────────────────────────────────
    def touch_ended(self, t):
        x, y = t.location

        def inside(btn):
            fx, fy, fw, fh = btn.frame
            return fx <= x <= fx + fw and fy <= y <= fy + fh

        for b in (self.btn_correct, self.btn_wrong, self.btn_back,
                  self.menu_btn, self.exit_btn):
            if inside(b):
                return
        self.show_mean = not self.show_mean
        self.present_card()

# ──────────────────────────────────────────
#  エントリーポイント
# ──────────────────────────────────────────
def main():
    ch = console.alert('カード順序', 'どの順序で始めますか?', '順番どおり', 'ランダム')
    CardView(WORDS, shuffle_first=(ch == 2)).present('fullscreen', hide_title_bar=True)

if __name__ == '__main__':
    main()
