import streamlit as st
from collections import namedtuple
import imaplib
from queue import LifoQueue as Stack
import re
import base64


send_to = st.sidebar.text_input('To: ')
send_cc = st.sidebar.text_input('Cc: ')
sender = st.sidebar.text_input('From: ', 'sp')


def main():
    st.write(st.secrets['mail'])
    conn = imaplib.IMAP4_SSL(st.secrets['mail']['server'])
    conn.login(st.secrets['mail']['user'], st.secrets['mail']['passwd'])
    conn.select()

    code, mess = conn.search(None, '(BEFORE 1-Oct-2021)')
    print(code, mess)
    if code == 'OK':
        nums = mess[0].decode().split()
        if nums:
            conn.store(','.join(nums), '+FLAGS', '\\Deleted')
    return
    code, mess = conn.search(None, '(SINCE 1-Mar-2022)')
    if code != 'OK':
        return

    stat, data = conn.fetch(','.join(mess[0].decode().split()), 'ENVELOPE')
    # print(data)
    st.table([parse_envelope(e) for e in data])

    # parse_envelope(data[0])

    # st.write([email.message_from_bytes(e).subject for e in data])

    # for e in data:
    #     m = email.message_from_bytes(e[1]) if len(e) > 1 else None
    #     print(email.header.decode_header(m['subject']) if m else None)
    #     print((m['Subject'], 'gb2312') if m else 'None')


def tokenize(mess):
    """
    separate by white space 32
    except:
    1. in quotes 34
    2. in parentheses 40, 41
    """
    left, pos, quotes, parentheses = 0, 0, 0, 0
    while pos < len(mess) - 1:
        pos += 1
        if mess[pos] == 34:
            quotes += 1 if quotes == 0 else -1
        if mess[pos] == 40:
            parentheses += 1
        if mess[pos] == 41:
            parentheses -= 1

        if mess[pos] == 32:
            if quotes > 0:
                continue
            elif parentheses > 0:
                continue
            print(mess[left:pos])
            left = pos + 1


def parse_envelope(mes):
    if not isinstance(mes, bytes):
        print(mes)
        return None, None, None

    res = re.search(r'(\d+) \(ENVELOPE \("([^"]+)" "=\?([^\?]+)\?(?:B|b)\?([^"]+)\?="', mes.decode())
    if not res:
        print(mes)
        return None, None, None
    num, dt, cs, sub = res.groups()
    sub = base64.b64decode(sub).decode(cs)

    return num, dt, sub


if __name__ == '__main__':
    main()
