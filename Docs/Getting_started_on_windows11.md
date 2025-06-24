
# DevDataClient – Getting Started on Windows


## 1. Open the Terminal

To start DevDataClient on Windows, the first step is to open a terminal.

You can do this in two ways:

- **Option A:** Use the Windows search bar (see screenshot) and type `cmd`, then press Enter.
(https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/WindowsLeiste.png?raw=true)

- **Option B:** Press `Windows + R` on your keyboard. A small window will appear (see screenshot); type `cmd` and press Enter.

(https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/cmd.png?raw=true)

Now you should be inside the terminal window.

---

## 2. Install Git

To use Git in the terminal, you need to install it first.

- Download the installer for Windows here: [https://git-scm.com/download/win](https://git-scm.com/download/win)
- Run the `.exe` file and follow the installation steps.
- After installation, you can use either **Git Bash** or the standard **Command Prompt / PowerShell**.

To verify Git was installed correctly, run the following command:

```bash
git --version
```
## 3. Clone the Repository

Now we’re ready to clone the project repository. Run the following command in your terminal:
```bash
 git clone https://github.com/AI-Gruppe/OmnAIView-python.git
```
(https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/clone.png?raw=true)

## 4. Navigate into the Project Directory

```bash
cd OmnAIView-python
```

## 5. Create a Virtual Environment

We’ll now set up a virtual environment to manage the project dependencies:

```bash 
python3.12 -m venv .venv
```

## 6. Activate the Virtual Environment

To activate the environment, run:

```bash
.venv\Scripts\Activate.ps1
```
If the command line now starts with (.venv) – everything is working correctly.

(https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/cdvenvstart.png?raw=true)

## 7. Install Project Dependencies

While the virtual environment is active, install the required dependencies:

```bash
pip install -r requirements.txt
```
This may take a minute or two depending on your internet speed.

(https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/req.png?raw=true)

## 8. Start the Application

Now you're ready to launch the project:


```bash
python .\src\main.py
```
A start menu should appear.

(https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/Start.png?raw=true)

## 9. Connect to WebSocket

The main interface will open. Click on "Connect to WebSocket" to initiate a connection.

## 10. Enter Server Address

A new window will appear where you can enter the IP:PORT of the server you want to connect to.

(https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/ipport.png?raw=true)

## 11. Start Working

Once connected, you can begin sending, receiving, and visualizing data.

(https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/Graph.png?raw=true)

