import os

class Config():
    HOST = os.getenv('HOST')
    COLLECTOR_CONNECT = os.getenv('COLLECTOR_CONNECT')

    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO' if ENVIRONMENT == 'production' else 'DEBUG').upper()

    @staticmethod
    def validate():
        required = {
            'HOST': Config.HOST,
            'COLLECTOR_CONNECT': Config.COLLECTOR_CONNECT,
        }
        for key, val in required.items():
            if not val:
                raise ValueError(f"{key} is not set")