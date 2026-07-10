# test_eventstream.py

import asyncio
import time

import slowlette


class App(slowlette.App):
    @slowlette.get('/')
    def index(self):
        return slowlette.Response(content=index_html, content_type='text/html')


    @slowlette.eventstream('/events')
    async def events(self, eventstream:slowlette.EventStream):
        await eventstream.accept()
        print("EventStream Connected")

        disconnect_task = asyncio.create_task(eventstream.wait_disconnected())
        count = 0

        try:
            while True:
                await eventstream.send({
                    'count': count,
                    'time': time.strftime('%H:%M:%S'),
                }, event='tick', id=str(count))

                sleep_task = asyncio.create_task(asyncio.sleep(1))
                done, pending = await asyncio.wait(
                    [sleep_task, disconnect_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if sleep_task in pending:
                    sleep_task.cancel()
                if disconnect_task in done:
                    await disconnect_task

                count += 1

        except slowlette.EventStreamConnectionClosed:
            print("EventStream Closed by client")

        finally:
            disconnect_task.cancel()
            try:
                await eventstream.close()
            except Exception:
                pass



index_html = """
<!DOCTYPE html>
<html lang="en">
<body>
  <h3>EventStream - Slow Tick Server</h3>
  <button id="connect">Connect</button>
  <button id="disconnect">Disconnect</button>
  <div id="messages"></div>
<script>
    let source = null;

    const connectButton = document.getElementById("connect");
    const disconnectButton = document.getElementById("disconnect");

    connectButton.addEventListener("click", () => {
        if (source !== null) {
            appendMessage("[already connected]");
            return;
        }

        source = new EventSource("/events");
        source.onopen = () => {
            appendMessage("[connected]");
        };
        source.onerror = () => {
            appendMessage("[error or closed]");
            source.close();
            source = null;
        };
        source.addEventListener("tick", (event) => {
            const doc = JSON.parse(event.data);
            appendMessage(`tick #${event.lastEventId}: ${doc.time}`);
        });
    });

    disconnectButton.addEventListener("click", () => {
        if (source === null) {
            appendMessage("[not connected]");
            return;
        }
        source.close();
        source = null;
        appendMessage("[closed by browser]");
    });

    function appendMessage(msg) {
        const messages = document.getElementById("messages");
        const entry = document.createElement("p");
        entry.textContent = msg;
        messages.appendChild(entry);
    }
</script>
</body>
</html>
"""

app = App()


if __name__ == '__main__':
    app.run()
