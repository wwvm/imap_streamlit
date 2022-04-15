from contextlib import contextmanager
from itertools import groupby
from datetime import datetime, timedelta
import re
import csv

import streamlit as st
from pyzabbix.api import ZabbixAPI
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from fitter import Fitter, get_common_distributions
import matplotlib.pyplot as plt


def main():
    st.set_page_config(layout="wide")

    st.sidebar.title('Baseline calculation')
    hosts = get_hosts()

    host_selected = st.sidebar.selectbox('Select Host', hosts, format_func=lambda x: x['host'])
    # print(host_selected)
    items = get_items(host_selected)
    intf_selected = st.sidebar.selectbox('Select Interface', items[0])
    item_selected = st.sidebar.selectbox('Select Item', items[1])

    item_ids = [e['itemid'] for e in items[1][item_selected] if intf_selected in e['name']]
    period = st.sidebar.radio('Time range', ('Day', 'Week', 'Month'))

    if st.sidebar.button('Analyze'):
        print('Running...')
        get_trend_data(item_selected, item_ids, period)
    else:
        print('No item')


def get_trend_data(name, ids, period):
    with connect() as zbx:
        res = zbx.trend.get(itemids=ids, time_from=get_time_from(period),
                            output=['clock', 'value_avg', 'value_min', 'value_max'],
                            orderfield=['itemid', 'clock'], orderby=['ASC', 'ASC'])
        res = [{k: int(v) for (k, v) in e.items()} for e in res]
        df = pd.DataFrame.from_records(res)
        plot(df)
        with st.expander('See Data'):
            st.table(df)

        fig = Figure()
        ax = fig.subplots()
        st.subheader(f'{name} Distribution')
        sns.set_context("paper", font_scale=2)
        sns.histplot(pd.to_numeric(df['value_avg']), ax=ax, kde=True)
        ax.set_xlabel('Value average (bps)')
        st.pyplot(fig)

        # pd.to_numeric(df['value_avg']).plot.kde(ax=ax)
        # pd.to_numeric(df['value_avg']).plot.hist(density=True, ax=ax)
        # ax.set_xlabel('Value average (bps)')
        # st.pyplot(fig)

        f = Fitter(pd.to_numeric(df['value_avg'].values), distributions=get_common_distributions())
        # f.fit()
        f2, a2 = plt.subplots()
        f.fit()
        st.table(f.summary())
        st.pyplot(f2)
        return

        with open('data.csv', 'w') as of:
            w = csv.writer(of)
            w.writerow(['hours', 'min', 'avg', 'max'])
            for e in res:
                w.writerow([time_slot(e['clock']), e['value_min'], e['value_avg'], e['value_max']])
                st.write(e)


def plot(df):
    st.table(df.describe(datetime_is_numeric=True))
    df['hour'] = pd.to_datetime(df['clock'], unit='s').dt.hour
    st.table(df.groupby('hour')['value_avg'].describe(datetime_is_numeric=True))
    fig, ax = plt.subplots()
    kind = st.selectbox('Chart', ['bar', 'line'])
    df.groupby('hour')['value_avg', 'value_min', 'value_max'].mean().plot(kind=kind, ax=ax)
    st.pyplot(fig)


@st.cache
def time_slot(timestamp):
    return datetime.fromtimestamp(int(timestamp)).strftime('%H')


@st.cache
def get_time_from(period):
    dt = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    if period == 'Day':
        return int((dt + timedelta(days=-1)).timestamp())
    elif period == 'Week':
        return int((dt + timedelta(days=-7)).timestamp())
    else:
        return int((dt + timedelta(days=-30)).timestamp())


@contextmanager
def connect():
    api: ZabbixAPI = None
    try:
        api = ZabbixAPI(**st.secrets['zabbix'])
        yield api
    finally:
        if api and api.user:
            api.user.logout()


@st.cache(allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None, "builtins.weakref": lambda _: None})
def get_hosts():
    with connect() as zbx:
        res = zbx.hostgroup.get(output=[], selectHosts=['name', 'host'], filter={'name': '_dev'})
        return res[0]['hosts'] if res else []


def get_items(host):
    with connect() as zbx:
        res = zbx.item.get(output=['name', 'value_type'], host=host['host'], search={'name': 'interface'})
        intf = groupby(res, lambda x: re.sub('Interface (.*): .*', r'\1', x['name']))
        items = groupby(res, lambda x: re.sub('.*: (.*)', r'\1', x['name']))
        return {k: list(v) for (k, v) in intf}, {k: list(v) for (k, v) in items}

# @st.cache(allow_output_mutation=True, hash_funcs={"_thread.RLock": lambda _: None})
# def init():
#     return mysql.connector.connect(**st.secrets['mysql'])


# conn = init_db()


# def run_query(query):
#     with conn.cursor() as cur:
#         cur.execute(query)
#         return cur.fetchall()


if __name__ == '__main__':
    main()
