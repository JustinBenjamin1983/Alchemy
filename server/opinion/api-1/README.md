# How to deploy

If on windows use WSL and an Ubuntu image

Make sure you have the Azure CLI install and login

Make sure you have docker desktop installed and running

If on WSL:
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip zip bc
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash install

az login --use-device-code

In Docker Desktop:

Go to Settings → General and ensure “Use the WSL 2 based engine” is checked.
Microsoft Learn
+1

Go to Settings → Resources → WSL Integration and:

Turn on “Enable integration with my default WSL distro”, and

Turn on integration for Ubuntu explicitly.

# If edited in windows, CRLF to LF

sudo apt install -y dos2unix
dos2unix build_linux.sh

chmod +x build_linux.sh

sudo rm -rf .python_packages
