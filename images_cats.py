import time
import requests
import os
# from data import yd_token
import logging
import json
from urllib.parse import quote, unquote
from tqdm import tqdm
from typing import Optional, Dict, List
import argparse

# Создание собственного логгера
logger = logging.getLogger('my_logs')
logger.setLevel(logging.DEBUG)

# Обработчик: в файл
file_handler = logging.FileHandler('my_logs.log', mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s",
                                            datefmt="%Y-%m-%d %H:%M:%S"))

# Добавляем обработчик к логгеру
logger.addHandler(file_handler)

# Функция для получения токена
def get_yd_token(filename):
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'r', encoding='utf-8') as f:
            token = f.read().strip()
    else:
        token = input('Введите токен для Yandex.Disk: ').strip()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(token)
    return token

yd_token = get_yd_token('yd_token.txt')

class YandexAPI:
    """
    Класс для работы с API Яндекс.Диска: создание папки, загрузка файла,
    а также сохранение метаинформации о загруженных файлах.
    """

    def __init__(self, ydtoken: str, folder_name: str = 'py-fpy-spd_132') -> None:
        self.__ydtoken = ydtoken
        self.folder_name = folder_name

    @property
    def headers(self) -> dict:
        return {'Authorization': f'OAuth {self.__ydtoken}'}

    def invalid_token(self):
        logger.error("❌ Введен неверный токен")
        with open('yd_token.txt', 'w', encoding='utf-8') as f:
            f.write('')
        raise PermissionError("Неверный токен доступа")

    def create_folder(self) -> None:
        """Создание папки на Яндекс диске"""
        logger.debug(f'Создание на Яндекс диске папки {self.folder_name}')
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': self.folder_name}
        try:
            response = requests.put(url, headers=self.headers, params=params)
        except UnicodeEncodeError:
            self.invalid_token()
        if response.status_code == 201:
            logger.info(f"✅ Папка '{self.folder_name}' создана.")
        elif response.status_code == 409:
            logger.warning(f"⚠️ Папка '{self.folder_name}' уже существует.")
        elif response.status_code == 401:
            self.invalid_token()
        else:
            logger.error(f"❌ Ошибка при создании папки: {response.text}")
            raise Exception(f"❌ Ошибка при создании папки: {response.text}")

    def upload_file(self, url_img: str) -> Optional[Dict[str, int]] | None:
        """Загрузка файла на Яндекс диск"""
        logger.debug(f"Загрузка файла {unquote(url_img)} в папку {self.folder_name} на Яндекс диске")
        self.file_name = os.path.basename(unquote(url_img))
        for symb in ['.', ',', '?', '!', '@', '\'', '"', '\\', '/', ':', ';', '`']:
            if symb in self.file_name:
                self.file_name = self.file_name.replace(symb, '')
        self.file_name = self.file_name.replace(' ', '_') + '.jpg'
        self.disk_path = f'{self.folder_name}/{self.file_name}'
        upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        params = {'path': self.disk_path, 'url': url_img}
        upload_response = requests.post(upload_url, headers=self.headers, params=params)
        if upload_response.status_code in (201, 202):
            logger.info(f"✅ Файл '{self.file_name}' успешно загружен в папку '{self.folder_name}'.")
        else:
            logger.critical(f"❌ Ошибка при загрузке файла: {upload_response.text}")
            raise Exception(f"Ошибка при загрузке файла: {upload_response.text}")
        return self._get_info_file()
    def _get_info_file(self) -> Optional[Dict[str, int]] | None:
        info_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': self.disk_path}
        timeout = 30
        for _ in range(timeout):
            info_response = requests.get(info_url, headers=self.headers, params=params)
            if info_response.status_code == 200:
                size = info_response.json().get('size')
                return {'name': self.file_name, 'size': size}
            time.sleep(1)
        else:
            logger.error(f"❌ Ошибка при получении информации о файле: {info_response.text}")
            return None


    @staticmethod
    def read_json_info() -> List[dict] | List:
        """
        Чтение мета информации из json-файла
        Если файл пустой или не существует, возвращает пустой список
        """
        try:
            with open('meta_info.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    @staticmethod
    def save_meta_info(meta_data: dict) -> None:
        """Сохранение информации о размере изображения в json-файл"""
        data = YandexAPI.read_json_info()
        data.append(meta_data)
        with open('meta_info.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            logger.info("Сохранение информации о размере фото")
            logger.info('\n'+'='*60+'\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Париснг надписей для изображения')
    parser.add_argument('--inscription', nargs='+', help='Текст, содержащий несколько надписей')
    args = parser.parse_args()
    list_image_text = args.inscription
    flag = not bool(list_image_text)
    while flag:
        image_text = input('Введите надпись для изображения с котом (или 0 для завершения ввода): ')
        if image_text == '0':
            break
        list_image_text.append(image_text)
    for img_text in list_image_text:
        url_image = rf"https://cataas.com/cat/says/{quote(img_text)}"

        with tqdm(total=3, desc='Начало работы') as progress:
            # Работа с Яндекс Диском
            ya_disk = YandexAPI(yd_token)
            progress.set_description("Создание папки")
            ya_disk.create_folder()
            progress.update(1)
            progress.set_description("Загрузка файла")
            meta_data = ya_disk.upload_file(url_image)
            progress.update(1)
            if meta_data:
                progress.set_description("Сохранение информации")
                ya_disk.save_meta_info(meta_data)
                progress.update(1)
    with open('meta_info.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    count = len(list_image_text)
    total_size = sum(item['size'] for item in data[-count:])
    print(f'Загружено {count} файл(а,ов), Всего: {total_size} КБ')