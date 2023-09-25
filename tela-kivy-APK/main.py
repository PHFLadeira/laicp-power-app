import firebase_admin
from firebase_admin import credentials, db
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.switch import Switch
from kivy.uix.screenmanager import SlideTransition
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.uix.popup import Popup
import pandas as pd

#######################################################################################################

# TEMPERATURE.PY
import requests

apiKey = "7f86f90fa68746dd7eae70b7bd18c36f"  # Sua chave API real
baseURL = "https://api.openweathermap.org/data/2.5/weather?q="

cityName = 'Manaus'

completeURL = baseURL + cityName + '&appid=' + apiKey

response = requests.get(completeURL)
data = response.json()

# Verifique o código de status da resposta
if data["cod"] != "404":
    temperatura_k = data["main"]["temp"]
    umidade = data["main"]["humidity"]
    temperatura_fahrenheit = (temperatura_k - 273.15) * 9/5 + 32  # Convertendo para Fahrenheit

#######################################################################################################

# APIMODEL.PY

import pickle
import pandas as pd

# Carregar o modelo e o scaler
with open("modelXGBoost.pkl", "rb") as f:
    modelo = pickle.load(f)

with open("scaler_x.pkl", "rb") as f:
    scaler_x = pickle.load(f)

with open("scaler_y.pkl", "rb") as f:
    scaler_y = pickle.load(f)

# Usando a variável importada como a temperatura média e a umidade média
temp_avg = temperatura_fahrenheit
hum_avg = umidade

#######################################################################################################

# Inicialização do Firebase
cred = credentials.Certificate("C:/Users/pedro/OneDrive/Área de Trabalho/Projeto_STEM_Teste_Site/controlelampada/laicp_power_key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://laicp-power-default-rtdb.firebaseio.com'
})

ref = db.reference()

# Tamanho da Tela Kivy
Window.size = (350, 550)

# Lista para manter o controle dos dispositivos que estão ligados
devices_on = []
peoplelab = ref.child('people').get()

# Navbar para navegação
class NavBar(BoxLayout):
    def __init__(self, **kwargs):
        super(NavBar, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint = (1, 0.1)

        
        self.dashboard_button = Button(text='Predict', on_press=self.switch_to_predict)
        self.home_button = Button(text='Home', on_press=self.switch_to_home)
        self.profile_button = Button(text='Profile', on_press=self.switch_to_profile)

        self.add_widget(self.dashboard_button)
        self.add_widget(self.home_button)
        self.add_widget(self.profile_button)

    def switch_to_predict(self, instance):
        app = App.get_running_app()
        app.root.transition = SlideTransition(direction='right')
        app.root.current = 'predict'

    def switch_to_home(self, instance):
        app = App.get_running_app()
        app.root.transition = SlideTransition(direction='down')
        app.root.current = 'main'


    def switch_to_profile(self, instance):
        app = App.get_running_app()
        app.root.transition = SlideTransition(direction='left')
        app.root.current = 'profile'

class LoginPage(Screen):
    def __init__(self, **kwargs):
        super(LoginPage, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(TextInput(hint_text='Username', multiline=False))
        layout.add_widget(TextInput(hint_text='Password', password=True, multiline=False))
        layout.add_widget(Button(text='Login', on_press=self.check_password))
        self.add_widget(layout)

    def check_password(self, instance):
        self.manager.current = 'main'

class ToggleSwitch(Switch):
    def __init__(self, device_name, **kwargs):
        super().__init__(**kwargs)
        self.device_name = device_name
        self.bind(active=self.toggle_device_status)
        self.update_switch_status()
        ref.child(self.device_name).listen(self.update_switch_status)

    
    def update_switch_status(self, *args):
        global devices_on, peoplelab
        peoplelab = ref.child('people').get()
        device_status = ref.child(self.device_name).get()
        self.active = (device_status == '1')

    def toggle_device_status(self, instance, value):
        global devices_on, peoplelab
        peoplelab = ref.child('people').get()
        if value:
            max_devices = 0
            if peoplelab <= 0:
                max_devices = 0
            elif peoplelab <= 4:
                max_devices = 3
            elif peoplelab <= 8:
                max_devices = 6
            else:
                max_devices = 9

            if len(devices_on) >= max_devices:
                self.confirmation_popup(instance, f"Tem {peoplelab} pessoa(s) no laboratório\n tem certeza que quer ligar mais lâmpadas?")
            else:
                self.proceed_with_toggling(instance, value)
        else:
            self.proceed_with_toggling(instance, value)

    def confirmation_popup(self, instance, message):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=message))
        buttons = BoxLayout()
        
        yes_button = Button(text="Sim")
        yes_button.bind(on_press=lambda x: self.proceed_with_toggling(instance, True))
        yes_button.bind(on_press=lambda x: popup.dismiss())
        buttons.add_widget(yes_button)

        no_button = Button(text="Não")
        no_button.bind(on_press=lambda x: self.proceed_with_toggling(instance, False))
        no_button.bind(on_press=lambda x: popup.dismiss())
        buttons.add_widget(no_button)
        
        content.add_widget(buttons)
        
        popup = Popup(title="Aviso", content=content, size_hint=(0.4, 0.4))
        popup.open()

    def proceed_with_toggling(self, instance, value):
        global devices_on
        app = App.get_running_app()
        device_screen = app.root.get_screen('main')
        
        if value:
            ref.child("Devices").child(self.device_name).set("1")
            if self.device_name not in devices_on:
                devices_on.append(self.device_name)
        else:
            ref.child("Devices").child(self.device_name).set("0")
            instance.active = False
            if self.device_name in devices_on:
                devices_on.remove(self.device_name)

        device_screen.update_devices_on_label()  # Atualiza o Label na tela de controle
        device_screen.update_people_on_label()  # Atualiza o Label na tela de controle

class PredictScreen(Screen):

    def __init__(self, **kwargs):
        super(PredictScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')

        self.temperature_label = Label(text=f"Temperatura atual em Manaus: {((round(temp_avg) - 32) * 5 / 9)} °C", size_hint=(0.9, 0.1))  # Alterado aqui
        self.layout.add_widget(self.temperature_label)
        
        self.consumption_input = TextInput(hint_text='Consumo atual', multiline=False, size_hint=(0.9, 0.1))  # Alterado aqui
        self.layout.add_widget(self.consumption_input)
        
        self.predict_button = Button(text="Prever consumo do dia seguinte", size_hint=(0.9, 0.1), on_press=self.predict_consumption)  # Alterado aqui
        self.layout.add_widget(self.predict_button)
        
        self.add_widget(self.layout)
        self.layout.add_widget(NavBar())
        
    def predict_consumption(self, instance):
        try:
            # Pegando o valor do consumo inserido pelo usuário
            consumption = float(self.consumption_input.text)
            
            # Criando o DataFrame
            entrada = pd.DataFrame([[temp_avg, hum_avg, consumption]], columns=['Temp_avg', 'Hum_avg', 'consumption'])
            
            # Escalando os dados
            entrada_scaled = scaler_x.transform(entrada)
            
            # Fazendo a previsão
            previsao = modelo.predict(entrada_scaled)
            
            # Desfazendo o escalonamento para mostrar a previsão na escala original
            previsao = scaler_y.inverse_transform([previsao])
            
            # Calculando o custo
            tarifa = 0.5  # exemplo de tarifa em R$/kWh
            previsao_kWd = previsao[0]
            custo_previsao = previsao_kWd * tarifa
            
            # Mostrando a previsão em um popup
            popup = Popup(title='Previsão do Consumo',
                          content=Label(text=f"A previsão do consumo em quilowatts: {previsao[0][0]}\nO custo previsto do consumo é: R$ {custo_previsao[0]:.2f}"),
                          size_hint=(0.8, 0.5))
            popup.open()
        except ValueError:
            # Caso o usuário não insira um número válido
            popup = Popup(title='Erro',
                          content=Label(text='Por favor, insira um número válido para o consumo.'),
                          size_hint=(0.8, 0.5))
            popup.open()

class DeviceControlScreen(Screen):
    def __init__(self, **kwargs):
        super(DeviceControlScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')

        with self.canvas.before:
            Color(0.8, 0.8, 0.8, 0)  # prata
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(size=self._update_rect, pos=self._update_rect)

        scroll_layout = GridLayout(cols=1, size_hint_y=None)
        scroll_layout.bind(minimum_height=scroll_layout.setter('height'))

        layout = GridLayout(cols=3, spacing=10, padding=20, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        self.devices_on_label = Label(text="", size_hint=(1, 0.1))
        self.people_on_label = Label(text="", size_hint=(1, 0.1))
        
        devices_lampadas = [
            "Lampada1", "Lampada2", "Lampada3", "Lampada4", "Lampada5", 
            "Lampada6", "Lampada7", "Lampada8", "Lampada9"
        ]

        self.create_buttons(devices_lampadas, layout)
        
        scroll_layout.add_widget(layout)
        scroll_view = ScrollView(size_hint=(1, 0.9), do_scroll_x=False)
        scroll_view.add_widget(scroll_layout)
        
        self.layout.add_widget(scroll_view)
        self.layout.add_widget(self.devices_on_label)
        self.layout.add_widget(self.people_on_label)
        self.layout.add_widget(NavBar())  
        self.add_widget(self.layout)
        

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def update_devices_on_label(self):
        self.devices_on_label.text = f"Dispositivos Ligados: {len(devices_on)}"

    def update_people_on_label(self):
        self.people_on_label.text = f"Pessoas no Laboratorio: {peoplelab}"
    
    def create_buttons(self, devices, layout):
        for device in devices:
            device_layout = GridLayout(cols=1, spacing=5, size_hint_y=None, height=150)
            label = Label(text=device, size_hint=(1, None), height=50)
            toggle_switch = ToggleSwitch(device_name=device, size_hint=(1, None), height=100)  # Use o ToggleSwitch aqui
            device_layout.add_widget(label)
            device_layout.add_widget(toggle_switch)
            layout.add_widget(device_layout)

class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super(ProfileScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')
        self.layout.add_widget(Label(text='Profile', size_hint=(1, 0.9)))
        self.layout.add_widget(NavBar())
        self.add_widget(self.layout)

class SwipeDetector:
    def __init__(self, callback, threshold=0.2):
        self.callback = callback
        self.threshold = threshold
        self.touch_down_x = 0
        self.touch_down_y = 0
        Window.bind(on_touch_down=self.on_touch_down)
        Window.bind(on_touch_up=self.on_touch_up)

    def on_touch_down(self, instance, touch):
        self.touch_down_x = touch.x
        self.touch_down_y = touch.y

    def on_touch_up(self, instance, touch):
        if self.is_swipe(touch):
            self.callback(touch)

    def is_swipe(self, touch):
        dx = touch.x - self.touch_down_x
        dy = touch.y - self.touch_down_y
        distance_moved = (dx ** 2 + dy ** 2) ** 0.5
        return distance_moved > Window.width * self.threshold

class MyApp(App):
    def build(self):
        self.navbar = NavBar()
        sm = ScreenManager()
        sm.add_widget(LoginPage(name='login'))
        sm.add_widget(PredictScreen(name='predict'))
        sm.add_widget(DeviceControlScreen(name='main'))
        sm.add_widget(ProfileScreen(name='profile'))

        self.swipe_detector = SwipeDetector(self.on_swipe)
        self.sm = sm  # Mantenha uma referência ao ScreenManager
        return sm

    def on_swipe(self, touch):
        dx = touch.x - self.swipe_detector.touch_down_x

        current_screen = self.sm.current  # Use a referência ao ScreenManager aqui
        next_screen = None
        transition_direction = 'left'

        if dx > 100:  # arrastar para a direita
            if current_screen == 'profile':
                next_screen = 'main'
                transition_direction = 'right'
            elif current_screen == 'main':
                next_screen = 'predict'
                transition_direction = 'right'
        elif dx < -100:  # arrastar para a esquerda
            if current_screen == 'predict':
                next_screen = 'main'
            elif current_screen == 'main':
                next_screen = 'profile'

        if next_screen:
            self.sm.transition = SlideTransition(direction=transition_direction)
            self.sm.current = next_screen

if __name__ == '__main__':
    MyApp().run()