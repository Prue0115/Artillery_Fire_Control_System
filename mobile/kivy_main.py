"""간단한 Kivy 기반 AFCS 계산기 샘플.

Buildozer로 APK를 만들 때 `source.main`에 이 파일을 지정하면
`rangeTables`와 `afcs` 로직을 그대로 활용하는 모바일 UI가 동작합니다.
"""

from kivy.app import App
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from afcs.equipment.registry import EquipmentRegistry
from afcs.range_tables import find_solution
from afcs.versioning import get_version


class CalculatorView(BoxLayout):
    result_text = StringProperty("장비와 수치를 입력한 뒤 계산을 눌러주세요.")

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=10, padding=16, **kwargs)

        self.registry = EquipmentRegistry()
        equipment_names = self.registry.names or ["장비 없음"]

        self.add_widget(Label(text="장비", size_hint_y=None, height=32))
        self.equipment_spinner = Spinner(text=equipment_names[0], values=equipment_names)
        self.add_widget(self.equipment_spinner)

        self.add_widget(Label(text="탄도 궤적 (high/low)", size_hint_y=None, height=32))
        self.trajectory_spinner = Spinner(text="high", values=["high", "low"])
        self.add_widget(self.trajectory_spinner)

        self.add_widget(Label(text="거리 (m)", size_hint_y=None, height=32))
        self.distance_input = TextInput(text="5000", input_filter="float", multiline=False)
        self.add_widget(self.distance_input)

        self.add_widget(Label(text="고도 차이(목표-사수, m)", size_hint_y=None, height=32))
        self.altitude_input = TextInput(text="0", input_filter="float", multiline=False)
        self.add_widget(self.altitude_input)

        calc_button = Button(text="계산", size_hint_y=None, height=48)
        calc_button.bind(on_press=self._on_calculate)
        self.add_widget(calc_button)

        self.result_label = Label(text=self.result_text, halign="left", valign="middle")
        self.result_label.bind(texture_size=self._update_label_size)
        self.add_widget(self.result_label)

    def _on_calculate(self, _instance):
        try:
            distance = float(self.distance_input.text)
            altitude = float(self.altitude_input.text)
        except ValueError:
            self.result_text = "거리/고도를 숫자로 입력하세요."
            self._sync_result()
            return

        equipment = self.registry.get(self.equipment_spinner.text)
        if equipment is None:
            self.result_text = "장비를 선택하세요."
            self._sync_result()
            return

        trajectory = self.trajectory_spinner.text
        solution = find_solution(distance, altitude, trajectory, equipment)
        if solution is None:
            self.result_text = "해당 조건에서 계산 결과를 찾을 수 없습니다."
        else:
            self.result_text = (
                f"Charge {solution['charge']}\n"
                f"Mill: {solution['mill']:.2f} (기본 {solution['base_mill']:.2f})\n"
                f"ETA: {solution['eta']:.2f}"
            )
        self._sync_result()

    def _sync_result(self):
        self.result_label.text = self.result_text

    def _update_label_size(self, instance, _value):
        instance.text_size = (self.width, None)
        instance.texture_update()


class AFCSMobileApp(App):
    def build(self):
        self.title = f"AFCS Mobile {get_version()}"
        return CalculatorView()


if __name__ == "__main__":
    AFCSMobileApp().run()
