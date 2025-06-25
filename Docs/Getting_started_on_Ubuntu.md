# DevDataClient – Getting Started on Ubuntu/Linux

## 1. Open the Terminal

To start working with DevDataClient on Linux, first open a terminal.

You can do this in two ways:

- **Option A:** Press `Ctrl + Alt + T` 
 
- **Option B:** Right-click Desktop and choose "Teminal"

![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/rightClick.png?raw=true)


---

## 2. Install Git

To use Git in Terminal you need to install it first.

```bash
sudo apt update && sudo apt install git
```

![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/gitinstall.png?raw=true)

To verify Git was installed correctly, run the following command:

```bash
git --version
```
## 3. Clone the Repository

Now we’re ready to clone the project repository. Run the following command in your terminal:

```bash
 git clone https://github.com/AI-Gruppe/OmnAIView-python.git
```
![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/gitCloneUb.png?raw=true)

## 4. Navigate into the Project Directory

Jump to Main-Projectrepository:

![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/CdUb.png?raw=true)

```bash
cd OmnAIView-python
```

## 5. Python Environment-Packages

To create and setup environments we need to install python3.12-venv by running :

```bash
sudo apt install python3.12-venv
```
![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/VenvInstall.png?raw=true)

## 6. Make sure Python3-tk is installed

To install python3-tk run:

```bash
sudo apt install python3-tk
```
![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/python3-tk.png?raw=true)

## 7. Create a Virtual Environment

We’ll now set up a virtual environment to manage the project dependencies:

```bash
python3.12 -m venv .venv1
```
![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/venvActivate.png?raw=true)

## 8. Activate the Virtual Environment

To activate the environment, run:

```bash
source ./.venv1/bin/activate
```
If the command line now starts with (.venv1) – everything is working correctly.

![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/venvActivate.png?raw=true)

## 7. Install Project Dependencies

While the virtual environment is active, install the required dependencies:

```bash
pip install -r requirements.txt
```
This may take a minute or two depending on your internet speed.

![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/reqUb.png?raw=true)

## 8. Start the Application

Now you're ready to launch the project:


```bash
python .\src\main.py
```
A start menu should appear.

![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/startUbConn.png?raw=true)

## 9. Connect to WebSocket

The main interface will open. Click on "Connect to WebSocket" to initiate a connection.

## 10. Enter Server Address

A new window will appear where you can enter the IP:PORT of the server you want to connect to.

![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/ipportUb.png?raw=true)

## 11. Start Working

Once connected, you can begin sending, receiving, and visualizing data.

![](https://github.com/Defjoint777/OmnAIView-python/blob/master/Docs/screens/screens/Graph.png?raw=true)
