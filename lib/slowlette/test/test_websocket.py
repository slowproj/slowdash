# test_websocket.py

import slowlette

class App(slowlette.App):
    @slowlette.get('/')
    def index(self):
        return slowlette.Response(content=index_html, content_type='text/html')


    @slowlette.websocket('/ws')
    async def ws_echo(self, request:slowlette.Request, websocket:slowlette.WebSocket):
        await websocket.accept()
        print(f"WebSocket Connected: {request}")
        await websocket.send(f'Your request is: {request}')
        try:
            while True:
                message = await websocket.receive()
                await websocket.send(f'Received: {message}')
        except slowlette.ConnectionClosed:
            print("WebSocket Closed")


            
index_html = """
<!DOCTYPE html>
<html lang="en">
<body>
  <h3>WebSocket - Slow Echo Server</h3>
  <input type="text" id="to_send" placeholder="type a message">
  <button id="send">Send</button>
  <div id="messages"></div>
<script>
    const socket = new WebSocket("ws://localhost:8000/ws");
    socket.onopen = () => {
        appendMessage("[connected]");
    };
    socket.onclose = () => {
        appendMessage("[closed]");
    };
    socket.onerror = (error) => {
        appendMessage("[error]" + error);
    };
    socket.onmessage = (event) => {
        appendMessage(`Server: ${event.data}`);
    };

    const to_send = document.getElementById("to_send");
    const button = document.getElementById("send");
    button.addEventListener("click", ()=>{
        const msg = to_send.value;
        to_send.value = "";
        if (! msg) {
            return;
        }
        appendMessage(`You: ${msg}`);
        if (socket.readyState != WebSocket.OPEN) {
            appendMessage(`[socket is not open]`);
            return;
        }
        socket.send(msg);
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
