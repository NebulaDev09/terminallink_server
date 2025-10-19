#this code runs on my hopes and dreams

import asyncio
import json

clients = set() #list of all clients conected to server
rooms = {}  #dictionary with room names as the key and all users in a list
writer_to_room = {}  #client with its current room (yes i could have used the previous one but no)


async def handle_clients(reader, writer):
    clients.add(writer)
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            try:
                message = json.loads(data.decode())
            except Exception:
                #we dont talk about exceptions
                continue

            mtype = message['type']
            if mtype == 'message' or mtype == 'file':
                await sendMessages(message, writer)
            elif mtype == 'server' and message.get('event') == 'connected':
                #when the client connects, send it the room list
                await sendRoomList(writer)
            elif mtype == 'system' and message.get('event') == 'roomJoin':
                room = message['room']
                if room not in rooms: #user created new room
                    rooms[room] = []
                if writer not in rooms[room]: #add client to the room list
                    rooms[room].append(writer)
                    writer_to_room[writer] = room
                notify = {
                    'type': 'system',
                    'event': 'connected',
                    'username': message['username']
                }
                for client in list(rooms[room]):
                    if client is not writer:
                        try:
                            client.write((json.dumps(notify) + '\n').encode())
                            await client.drain()
                        except Exception:
                            #remove clients that cannot be contacted
                            if client in clients:
                                clients.remove(client)
                            if client in rooms.get(room, []):
                                rooms[room].remove(client)

    finally:
        #remove clients when they disconnect
        if writer in clients:
            clients.remove(writer)
        room = writer_to_room.pop(writer)
        if room:
            if writer in rooms.get(room, []):
                rooms[room].remove(writer)
            #notify other clients in the room
            notify = {'type': 'system', 'event': 'disconnected', 'username': ''}
            for client in list(rooms.get(room, [])):
                try:
                    client.write((json.dumps(notify) + '\n').encode())
                    await client.drain()
                except Exception:
                    if client in clients:
                        clients.remove(client)
                    if client in rooms.get(room, []):
                        rooms[room].remove(client)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def sendMessages(message, sender_writer):
    sender_room = writer_to_room.get(sender_writer)
    if not sender_room:
        return
    for client in list(rooms.get(sender_room, [])):
        if client is not sender_writer:
            try:
                client.write((json.dumps(message) + '\n').encode())
                await client.drain()
            except Exception:
                if client in clients:
                    clients.remove(client)
                if client in rooms.get(sender_room, []):
                    rooms[sender_room].remove(client)


async def sendRoomList(writer): #send room list to client
    try:
        room_counts = {r: len(writers) for r, writers in rooms.items()}
        writer.write((json.dumps(room_counts) + '\n').encode())
        await writer.drain()
    except Exception:
        pass


async def main():
    server = await asyncio.start_server(handle_clients, '192.168.29.153', 6767)
    async with server:
        await server.serve_forever()


asyncio.run(main())
