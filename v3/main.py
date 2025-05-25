import requests
import json
import schedule
import time

CONFIG_FILE = "config.json"

#CHANGELOG
#Added auth token refreshing every 10 mins
def load_config():
    """
    Loads configuration data from the JSON file.
    This now includes server address, username, password, and times.
    """
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{CONFIG_FILE}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{CONFIG_FILE}'. Please check the file format.")
        return None

def get_access_token(server_address, username, password):
    """
    Retrieves the access token from the login API.

    Args:
        server_address (str): The base URL of the restreamer server.
        username (str): The username for authentication.
        password (str): The password for authentication.

    Returns:
        str: The access token, or None if an error occurs.
    """
    login_url = f"{server_address}/api/login"
    try:
        payload = {
            "username": username,
            "password": password
        }
        response = requests.post(login_url, json=payload)
        response.raise_for_status()

        data = response.json()
        access_token = data.get("access_token")  # Adjust this key if needed
        if access_token:
            return access_token
        else:
            print("Error: Access token not found in login response.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error during login: {e}")
        return None
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from login.")
        return None

def refresh_access_token(server_address, username, password):
    """
    Refreshes the access token by logging in again.

    Args:
        server_address (str): The base URL of the restreamer server.
        username (str): The username for authentication.
        password (str): The password for authentication.

    Returns:
        str: The new access token, or None if an error occurs.
    """
    login_url = f"{server_address}/api/login"
    try:
        payload = {
            "username": username,
            "password": password
        }
        response = requests.post(login_url, json=payload)
        response.raise_for_status()

        data = response.json()
        access_token = data.get("access_token")  # Adjust this key if needed
        if access_token:
            print("Successfully refreshed access token.")
            return access_token
        else:
            print("Error: Access token not found in refresh response.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error during token refresh: {e}")
        return None
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from token refresh.")
        return None

def send_restreamer_command(server_address, process_id, authorization_token, payload, is_snapshot=False):
    """
    Sends a command to the restreamer API (start or stop).
    This function now constructs the API URLs dynamically.
    """
    process_identifier = f"restreamer-ui%3Aingest%3A{process_id}"
    if is_snapshot:
        process_identifier += "_snapshot"
    command_url = f"{server_address}/api/v3/process/{process_identifier}/command"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {authorization_token}"
    }

    try:
        response = requests.put(command_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"{payload['command'].capitalize()} command sent successfully to process '{process_id}'. Response:")
        print(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error sending command to process '{process_id}': {e}")
    except json.JSONDecodeError:
        print("Error decoding JSON response.")

def connect_stream(config):
    """
    Connects the stream by sending 'start' commands.
    """
    print(f"Connecting stream at {time.strftime('%H:%M:%S')}")
    send_restreamer_command(config['server_address'], config['process_id'], config['authorization_token'], {"command": "start"})
    send_restreamer_command(config['server_address'], config['process_id'], config['authorization_token'], {"command": "start"}, is_snapshot=True)
    print("Stream connection initiated.")

def disconnect_stream(config):
    """
    Disconnects the stream by sending 'stop' commands.
    """
    print(f"Disconnecting stream at {time.strftime('%H:%M:%S')}")
    send_restreamer_command(config['server_address'], config['process_id'], config['authorization_token'], {"command": "stop"}, is_snapshot=True)
    send_restreamer_command(config['server_address'], config['process_id'], config['authorization_token'], {"command": "stop"})
    print("Stream disconnection initiated.")

if __name__ == "__main__":
    config = load_config()

    if config:
        # Get login info and attempt to retrieve token
        server_address = config.get("server_address")
        username = config.get("username")
        password = config.get("password")

        if server_address and username and password:
            access_token = get_access_token(server_address, username, password)
            if access_token:
                config['authorization_token'] = access_token
                print("Successfully retrieved access token.")
            else:
                print("Error: Could not retrieve access token. Script will exit.")
                exit()
        else:
            print("Error: Missing login credentials in config. Script will exit.")
            exit()

        connect_time = config.get("connect_time")
        disconnect_time = config.get("disconnect_time")

        if connect_time:
            schedule.every().day.at(connect_time).do(connect_stream, config=config)
            print(f"Scheduled stream connection for {connect_time} daily.")
        else:
            print("Warning: 'connect_time' not found in config file.")

        if disconnect_time:
            schedule.every().day.at(disconnect_time).do(disconnect_stream, config=config)
            print(f"Scheduled stream disconnection for {disconnect_time} daily.")
        else:
            print("Warning: 'disconnect_time' not found in config file.")

        # Schedule token refresh every 10 minutes
        schedule.every(10).minutes.do(
            refresh_access_token,
            server_address=server_address,
            username=username,
            password=password,
        )
        print("Scheduled token refresh every 10 minutes.")

        while True:
            schedule.run_pending()
            time.sleep(1)

            user_input = input("Enter 'c' to connect, 'd' to disconnect, or 'q' to quit: ").lower()

            if user_input == 'c':
                connect_stream(config)
            elif user_input == 'd':
                disconnect_stream(config)
            elif user_input == 'q':
                print("Exiting.")
                break
            elif user_input:
                print("Invalid input. Please enter 'c', 'd', or 'q'.")
#This is line 200