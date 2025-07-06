# auth.py
import streamlit as st
import xmlrpc.client
import json
from cryptography.fernet import Fernet
import pickle
import hashlib
import datetime
import os
from odoo_connector import connect_to_odoo, get_current_user_employee_data

# Cache directory for storing credentials and connection data
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".prezlab_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Credential storage configuration
CREDENTIAL_FILE = os.path.join(CACHE_DIR, "credentials.enc")
KEY_FILE = os.path.join(CACHE_DIR, "key.key")
CONNECTION_CACHE_FILE = os.path.join(CACHE_DIR, "connection_cache.pkl")

class CredentialManager:
    """Securely store and retrieve user credentials"""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self):
        """Get existing key or create a new one"""
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(KEY_FILE, 'wb') as f:
                f.write(key)
            return key
    
    def save_credentials(self, username, password):
        """Save encrypted credentials"""
        credentials = {
            'username': username,
            'password': password,
            'timestamp': datetime.datetime.now().isoformat()
        }
        encrypted = self.cipher.encrypt(json.dumps(credentials).encode())
        
        with open(CREDENTIAL_FILE, 'wb') as f:
            f.write(encrypted)
    
    def load_credentials(self):
        """Load and decrypt credentials"""
        if not os.path.exists(CREDENTIAL_FILE):
            return None
        
        try:
            with open(CREDENTIAL_FILE, 'rb') as f:
                encrypted = f.read()
            
            decrypted = self.cipher.decrypt(encrypted)
            credentials = json.loads(decrypted.decode())
            
            # Check if credentials are not too old (30 days)
            timestamp = datetime.datetime.fromisoformat(credentials['timestamp'])
            if datetime.datetime.now() - timestamp > datetime.timedelta(days=30):
                self.clear_credentials()
                return None
            
            return credentials
        except Exception as e:
            self.clear_credentials()
            return None
    
    def clear_credentials(self):
        """Remove stored credentials"""
        if os.path.exists(CREDENTIAL_FILE):
            os.remove(CREDENTIAL_FILE)

class ConnectionCache:
    """Cache Odoo connection data to speed up subsequent logins"""
    
    @staticmethod
    def get_cache_key(username, db):
        """Generate a cache key based on username and database"""
        return hashlib.md5(f"{username}:{db}".encode()).hexdigest()
    
    @staticmethod
    def save_connection_data(username, db, uid, employee_data):
        """Save connection data to cache"""
        cache_key = ConnectionCache.get_cache_key(username, db)
        cache_data = {
            'uid': uid,
            'employee_data': employee_data,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Load existing cache
        cache = {}
        if os.path.exists(CONNECTION_CACHE_FILE):
            try:
                with open(CONNECTION_CACHE_FILE, 'rb') as f:
                    cache = pickle.load(f)
            except:
                cache = {}
        
        # Update cache
        cache[cache_key] = cache_data
        
        # Save updated cache
        with open(CONNECTION_CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    
    @staticmethod
    def get_connection_data(username, db):
        """Get cached connection data"""
        if not os.path.exists(CONNECTION_CACHE_FILE):
            return None
        
        cache_key = ConnectionCache.get_cache_key(username, db)
        
        try:
            with open(CONNECTION_CACHE_FILE, 'rb') as f:
                cache = pickle.load(f)
            
            if cache_key in cache:
                cache_data = cache[cache_key]
                # Check if cache is not too old (1 hour)
                timestamp = datetime.datetime.fromisoformat(cache_data['timestamp'])
                if datetime.datetime.now() - timestamp < datetime.timedelta(hours=1):
                    return cache_data
                else:
                    # Remove old cache entry
                    del cache[cache_key]
                    with open(CONNECTION_CACHE_FILE, 'wb') as f:
                        pickle.dump(cache, f)
            
            return None
        except:
            return None

def fast_connect_to_odoo(odoo_url, odoo_db, username, password, use_cache=True):
    """
    Fast connection to Odoo with caching and validation
    """
    # Check cache first
    if use_cache:
        cached_data = ConnectionCache.get_connection_data(username, odoo_db)
        if cached_data:
            # Validate the cached UID is still valid
            try:
                models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object', allow_none=True)
                # Quick validation call
                test = models.execute_kw(
                    odoo_db, cached_data['uid'], password,
                    'res.users', 'check_access_rights',
                    ['read'], {'raise_exception': False}
                )
                if test:
                    # Cache is valid
                    st.session_state.odoo_uid = cached_data['uid']
                    st.session_state.odoo_models = models
                    st.session_state.odoo_connected = True
                    st.session_state.db = odoo_db
                    st.session_state.password = password
                    st.session_state.employee_data = cached_data['employee_data']
                    st.session_state.auto_loaded = True
                    return True, "Connected to Odoo (cached)", "Connected successfully"
            except:
                pass
    
    # Normal connection - use existing connect_to_odoo function
    success, message, user_info = connect_to_odoo(odoo_url, odoo_db, username, password)
    
    if success and use_cache and st.session_state.get('employee_data'):
        # Cache the successful connection
        ConnectionCache.save_connection_data(
            username, odoo_db, 
            st.session_state.odoo_uid, 
            st.session_state.employee_data
        )
    
    return success, message, user_info

class AuthManager:
    def __init__(self, odoo_url, odoo_db):
        self.odoo_url = odoo_url
        self.odoo_db = odoo_db
        self.cred_manager = CredentialManager()
    
    def login(self, username, password, remember_me=False):
        """Enhanced login with credential saving and caching"""
        with st.spinner("Logging in..."):
            # Use fast connection with caching
            success, message, user_info = fast_connect_to_odoo(
                self.odoo_url, self.odoo_db, username, password, use_cache=True
            )
            
            if success:
                # Save credentials if remember me is checked
                if remember_me:
                    self.cred_manager.save_credentials(username, password)
                
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.password = password
                
                st.success("Login successful!")
                st.rerun()
            else:
                st.error(message)
                return False
        
        return True
    
    def logout(self):
        """Clear session and logout"""
        # Clear saved credentials first
        self.cred_manager.clear_credentials()
        
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()