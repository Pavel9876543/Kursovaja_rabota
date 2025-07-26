import requests
import os
from data import yd_token
import logging
import json
import urllib.parse
from tqdm import tqdm
from typing import Optional, Dict, List

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

class YandexAPI:
    """
    Класс для работы с API Яндекс.Диска: создание папки, загрузка файла,
    а также сохранение метаинформации о загруженных файлах.
    """

    def __init__(self, ydtoken: str, folder_name: str = 'py-fpy-spd_132', progress: Optional[tqdm] = None) -> None:
        self.ydtoken = ydtoken
        self.folder_name = folder_name
        self.progress = progress

    @property
    def headers(self) -> dict:
        return {'Authorization': f'OAuth {self.ydtoken}'}

    def create_folder(self) -> None:
        """Создание папки на Яндекс диске"""
        logger.debug(f'Создание на Яндекс диске папки {self.folder_name}')
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': self.folder_name}
        response = requests.put(url, headers=self.headers, params=params)

        if response.status_code == 201:
            logger.info(f"✅ Папка '{self.folder_name}' создана.")
        elif response.status_code == 409:
            logger.warning(f"⚠️ Папка '{self.folder_name}' уже существует.")
        else:
            logger.error(f"❌ Ошибка при создании папки: {response.text}")

        if self.progress:
            self.progress.set_description("Создание папки")
            self.progress.update(1)

    def upload_file(self, local_file_path: str) -> Optional[Dict[str, int]]:
        """Загрузка файла на Яндекс диск"""
        logger.debug(f"Загрузка файла {local_file_path} в папку {self.folder_name} на Яндекс диске")
        file_name = os.path.basename(local_file_path)
        disk_path = f'{self.folder_name}/{file_name}'
        upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        params = {'path': disk_path, 'overwrite': 'true'}

        response = requests.get(upload_url, headers=self.headers, params=params)
        if response.status_code != 200:
            logger.error(f"❌ Ошибка при получении ссылки для загрузки: {response.text}")
            return None

        href = response.json().get('href')
        if not href:
            logger.error("❌ Не удалось получить ссылку для загрузки")
            return None

        with open(local_file_path, 'rb') as file_data:
            upload_response = requests.put(href, data=file_data)

        if upload_response.status_code in (201, 202):
            logger.info(f"✅ Файл '{file_name}' успешно загружен в папку '{self.folder_name}'.")
        else:
            logger.critical(f"❌ Ошибка при загрузке файла: {upload_response.text}")
            raise Exception(f"Ошибка при загрузке файла: {upload_response.text}")

        info_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        params = {'path': disk_path}
        info_response = requests.get(info_url, headers=self.headers, params=params)

        if info_response.status_code != 200:
            logger.error(f"❌ Ошибка при получении информации о файле: {info_response.text}")
            return None

        file_info = info_response.json()
        size = file_info.get('size', 0)

        if self.progress:
            self.progress.set_description("Загрузка файла")
            self.progress.update(1)

        return {'name': file_name, 'size': size}

    @staticmethod
    def read_json_info() -> List[dict]:
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
    def save_meta_info(meta_data: dict, progress: Optional[tqdm] = None) -> None:
        """Сохранение информации о размере изображения в json-файл"""
        data = YandexAPI.read_json_info()
        data.append(meta_data)
        with open('meta_info.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            logger.info("Сохранение информации о размере фото")
            logger.info('\n'+'='*60+'\n')

        if progress:
            progress.set_description("Сохранение информации")
            progress.update(1)


def text_in_image_cat(text: str, save_folder: str, progress: Optional[tqdm] = None) -> str:
    """Функция для скачивания изображений с котами с сайта cataas.com
    с указанным текстом на картинке."""
    logger.debug(f"Скачивание картинки с котом и текстом: {text}")
    encoded = urllib.parse.quote(text)
    url = f'https://cataas.com/cat/says/{encoded}'

    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"❌ Ошибка получения изображения: {response.text}")

    safe_name = text
    for ch in ['@', '#', '%', '?', '!', ':', '"', "'", '<', '>', '/', '\\', '|', '*']:
        safe_name = safe_name.replace(ch, '')

    save_path = os.path.join(save_folder, f"{safe_name}.jpg")
    os.makedirs(save_folder, exist_ok=True)

    with open(save_path, 'wb') as f:
        f.write(response.content)

    logger.info(f"✅ Картинка с котом сохранена как: {save_path}")

    if progress:
        progress.set_description("Скачивание картинки")
        progress.update(1)

    return save_path

if __name__ == "__main__":
    save_folder = 'images'
    image_text = input('Введите надпись для изображения с котом: ')

    with tqdm(total=4, desc='Начало работы') as progress:
        # Скачивание изображения
        local_image_path = text_in_image_cat(image_text, save_folder, progress)

        # Работа с Яндекс Диском
        ya_disk = YandexAPI(yd_token, progress=progress)
        ya_disk.create_folder()

        meta_data = ya_disk.upload_file(local_image_path)
        if meta_data:
            ya_disk.save_meta_info(meta_data, progress)