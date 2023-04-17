import pandas as pd
import re
import logging
import time
from datetime import datetime


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Сравнение методов обработки файлов.

#Загружаем тестовый xls

schedule_raw = pd.read_excel(
    'schedule.xlsx',
    dtype=str,
    # usecols="A:F"
    # skiprows=[0, 1, 2, 3],
    # index_col=3,
    )


logger.debug(f'Excel file loaded.')
print(schedule_raw.columns)

# обработка excel. 
start = time.time()
ef = pd.DataFrame()
# d_js[['wbs', 'wbs2', 'wbs3_id', 'name']] = d[['Проект','Смета', 'Шифр', 'НаименованиеПолное' ]]
EXCHANGE_FORM_FIELDS = ['СПП', 'Проект', '№ локальной сметы','Наименование локальной сметы','№ п/п','Шифр','Код','Строка сметы','Предшественник','Объем','Единица измерения']
for field in EXCHANGE_FORM_FIELDS:
    ef[field] = schedule_raw[field]
ef['Плановая дата начала'] = schedule_raw['Реальная дата начала'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f').strftime('%d.%m.%Y'))
ef['Плановая дата окончания'] = schedule_raw['Реальная дата окончания'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f').strftime('%d.%m.%Y'))	

# Убрать из, кода. Но корректно выводить предшественника
ef['Предшественник'] = ef['Предшественник'].apply(lambda x: '')
   
print(ef.columns)
print(ef.head(5))

# Формирование название файла для выгрузки
name = ef['СПП'][0]
ef.to_excel(f'{name}.xlsx', index=False)

