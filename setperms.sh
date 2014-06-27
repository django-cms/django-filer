find . -type d -exec chmod 755 {} \;
find . -type f -exec chmod 644 {} \;
chmod +x setperms.sh
chmod +x runtests.py
chmod +x .travis_setup
