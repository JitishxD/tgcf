import os
import signal
import subprocess
import time

import streamlit as st
try:
    import psutil
except Exception:
    psutil = None

from tgcf.config import CONFIG, read_config, write_config
from tgcf.web_ui.password import check_password
from tgcf.web_ui.utils import hide_st, switch_theme

CONFIG = read_config()


def termination():
    st.code("process terminated!")
    os.rename("logs.txt", "old_logs.txt")
    with open("old_logs.txt", "r") as f:
        st.download_button(
            "Download last logs", data=f.read(), file_name="tgcf_logs.txt"
        )

    CONFIG = read_config()
    CONFIG.pid = 0
    write_config(CONFIG)
    st.button("Refresh page")


st.set_page_config(
    page_title="Run",
    page_icon="🏃",
)
hide_st(st)
switch_theme(st,CONFIG)
if check_password(st):
    with st.expander("Configure Run"):
        CONFIG.show_forwarded_from = st.checkbox(
            "Show 'Forwarded from'", value=CONFIG.show_forwarded_from
        )
        mode = st.radio("Choose mode", ["live", "past"], index=CONFIG.mode)
        if mode == "past":
            CONFIG.mode = 1
            st.warning(
                "Only User Account can be used in Past mode. Telegram does not allow bot account to go through history of a chat!"
            )
            CONFIG.past.delay = st.slider(
                "Delay in seconds", 0, 100, value=CONFIG.past.delay
            )
        else:
            CONFIG.mode = 0
            CONFIG.live.delete_sync = st.checkbox(
                "Sync when a message is deleted", value=CONFIG.live.delete_sync
            )

        if st.button("Save"):
            write_config(CONFIG)

    check = False

    if CONFIG.pid == 0:
        check = st.button("Run", type="primary")

    if CONFIG.pid != 0:
        st.warning(
            "You must click stop and then re-run tgcf to apply changes in config."
        )
        # check if process is running using pid
        try:
            if hasattr(signal, "SIGCONT"):
                os.kill(CONFIG.pid, signal.SIGCONT)
            elif psutil is not None:
                psutil.Process(CONFIG.pid).resume()
            else:
                st.warning(
                    "Resume not available: install psutil or use POSIX.")
        except Exception as err:
            st.code("The process has stopped.")
            st.code(err)
            CONFIG.pid = 0
            write_config(CONFIG)
            time.sleep(1)
            st.rerun()

        stop = st.button("Stop", type="primary")
        if stop:
            try:
                if hasattr(signal, "SIGSTOP"):
                    os.kill(CONFIG.pid, signal.SIGSTOP)
                elif psutil is not None:
                    psutil.Process(CONFIG.pid).suspend()
                else:
                    st.warning(
                        "Pause not available: install psutil or use POSIX.")
            except Exception as err:
                st.code(err)

                CONFIG.pid = 0
                write_config(CONFIG)
                st.button("Refresh Page")

            else:
                termination()

    if check:
        with open("logs.txt", "w") as logs:
            process = subprocess.Popen(
                ["tgcf", mode],
                stdout=logs,
                stderr=subprocess.STDOUT,
            )
        CONFIG.pid = process.pid
        write_config(CONFIG)
        time.sleep(2)

        st.rerun()

    try:
        lines = st.slider(
            "Lines of logs to show", min_value=100, max_value=1000, step=100
        )
        # Read last N lines of logs.txt in pure Python for cross-platform support
        with open("logs.txt", "r", encoding="utf-8", errors="ignore") as file:
            content = file.readlines()
        if not content:
            st.info("Logs are empty. The process may not have started yet.")
        else:
            tail = content[-lines:] if len(content) > lines else content
            st.code("".join(tail))
    except FileNotFoundError as err:
        st.write("No present logs found")
    if st.button("Load more logs"):
        st.rerun()
