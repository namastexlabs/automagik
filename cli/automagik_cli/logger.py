import logging
import click
from datetime import datetime
import pytz

class ColoredFormatter(logging.Formatter):
    """Custom formatter adding colors and timestamps to log messages"""
    
    COLORS = {
        'DEBUG': lambda x: click.style(x, fg='blue'),
        'INFO': lambda x: click.style(x, fg='green'),
        'WARNING': lambda x: click.style(x, fg='yellow'),
        'ERROR': lambda x: click.style(x, fg='red'),
        'CRITICAL': lambda x: click.style(x, fg='red', bold=True),
    }

    def format(self, record):
        # Add timezone info
        tz = pytz.timezone('America/Sao_Paulo')
        now = datetime.now(tz)
        
        # Format the message
        level_color = self.COLORS.get(record.levelname, lambda x: x)
        record.levelname = level_color(f"[{record.levelname}]")
        record.msg = f"{now.strftime('%Y-%m-%d %H:%M:%S %Z')} {record.msg}"
        
        return super().format(record)

def setup_logger(name='automagik', level=logging.INFO):
    """Setup and return a logger with colored output"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler with colored formatter
    ch = logging.StreamHandler()
    ch.setLevel(level)
    
    formatter = ColoredFormatter('%(levelname)s %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger
