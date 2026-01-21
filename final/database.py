"""
MarketSense AI - Database Module
Handles all database operations including candle data, trades, and user behavior.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
import config

class Database:
    """SQLite database handler for MarketSense AI."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Candle data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL DEFAULT 0,
                session TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(asset, timeframe, timestamp)
            )
        ''')
        
        # Trades table (simulated and manual-assist)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                entry_time DATETIME NOT NULL,
                exit_time DATETIME,
                amount REAL NOT NULL,
                pnl REAL DEFAULT 0,
                outcome TEXT,
                mode TEXT NOT NULL,
                strategy_score REAL,
                ai_probability REAL,
                ai_recommendation TEXT,
                indicators_snapshot TEXT,
                journal_entry TEXT,
                session TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User behavior tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_behavior (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session TEXT,
                notes TEXT
            )
        ''')
        
        # Rule violations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                violation_type TEXT NOT NULL,
                description TEXT,
                trade_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        ''')
        
        # Strategy performance
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                avg_score REAL DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # AI model metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_version TEXT,
                accuracy REAL,
                precision_score REAL,
                recall REAL,
                f1_score REAL,
                training_samples INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Daily summaries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                total_trades INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                best_trade_pnl REAL,
                worst_trade_pnl REAL,
                avg_score REAL,
                violations INTEGER DEFAULT 0,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Account balance history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                balance REAL NOT NULL,
                change_amount REAL DEFAULT 0,
                change_reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_candles_asset_time ON candles(asset, timeframe, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_asset ON trades(asset)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(entry_time)')
        
        conn.commit()
        conn.close()
    
    # ============================================
    # CANDLE DATA OPERATIONS
    # ============================================
    
    def insert_candle(self, asset: str, timeframe: str, timestamp,
                       open_price: float, high: float, low: float, close: float,
                       volume: float = 0, session: str = None) -> bool:
        """Insert a single candle into the database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Convert timestamp to string if needed
            if hasattr(timestamp, 'isoformat'):
                timestamp = timestamp.isoformat()
            elif hasattr(timestamp, 'strftime'):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT OR REPLACE INTO candles 
                (asset, timeframe, timestamp, open, high, low, close, volume, session)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (asset, timeframe, str(timestamp), open_price, high, low, close, volume, session))
            conn.commit()
            return True
        except Exception as e:
            # Silently ignore duplicate entries
            pass
            return False
        finally:
            conn.close()
    
    def insert_candles_bulk(self, df: pd.DataFrame, asset: str, timeframe: str) -> int:
        """Bulk insert candles from a DataFrame."""
        conn = self._get_connection()
        count = 0
        try:
            for _, row in df.iterrows():
                cursor = conn.cursor()
                # Convert timestamp to string if it's a Timestamp object
                timestamp = row.get('timestamp')
                if hasattr(timestamp, 'isoformat'):
                    timestamp = timestamp.isoformat()
                elif hasattr(timestamp, 'strftime'):
                    timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO candles 
                    (asset, timeframe, timestamp, open, high, low, close, volume, session)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (asset, timeframe, str(timestamp), float(row.get('open', 0)),
                      float(row.get('high', 0)), float(row.get('low', 0)), float(row.get('close', 0)),
                      float(row.get('volume', 0)), row.get('session')))
                count += 1
            conn.commit()
        except Exception as e:
            print(f"Error in bulk insert: {e}")
        finally:
            conn.close()
        return count
    
    def get_candles(self, asset: str, timeframe: str, limit: int = 500,
                    start_time: datetime = None, end_time: datetime = None) -> pd.DataFrame:
        """Retrieve candle data as DataFrame."""
        conn = self._get_connection()
        query = '''
            SELECT timestamp, open, high, low, close, volume, session
            FROM candles
            WHERE asset = ? AND timeframe = ?
        '''
        params = [asset, timeframe]
        
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time)
        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    # ============================================
    # TRADE OPERATIONS
    # ============================================
    
    def insert_trade(self, trade_data: Dict[str, Any]) -> int:
        """Insert a new trade and return its ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades 
            (asset, timeframe, direction, entry_price, exit_price, entry_time, exit_time,
             amount, pnl, outcome, mode, strategy_score, ai_probability, ai_recommendation,
             indicators_snapshot, journal_entry, session)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('asset'),
            trade_data.get('timeframe'),
            trade_data.get('direction'),
            trade_data.get('entry_price'),
            trade_data.get('exit_price'),
            trade_data.get('entry_time'),
            trade_data.get('exit_time'),
            trade_data.get('amount'),
            trade_data.get('pnl', 0),
            trade_data.get('outcome'),
            trade_data.get('mode', 'simulation'),
            trade_data.get('strategy_score'),
            trade_data.get('ai_probability'),
            trade_data.get('ai_recommendation'),
            trade_data.get('indicators_snapshot'),
            trade_data.get('journal_entry'),
            trade_data.get('session')
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id
    
    def update_trade(self, trade_id: int, update_data: Dict[str, Any]) -> bool:
        """Update an existing trade."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values()) + [trade_id]
        
        cursor.execute(f'UPDATE trades SET {set_clause} WHERE id = ?', values)
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def get_trades(self, limit: int = 100, asset: str = None,
                   start_date: datetime = None, end_date: datetime = None) -> pd.DataFrame:
        """Retrieve trades as DataFrame."""
        conn = self._get_connection()
        query = 'SELECT * FROM trades WHERE 1=1'
        params = []
        
        if asset:
            query += ' AND asset = ?'
            params.append(asset)
        if start_date:
            query += ' AND entry_time >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND entry_time <= ?'
            params.append(end_date)
        
        query += ' ORDER BY entry_time DESC LIMIT ?'
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    def get_trade_count(self) -> int:
        """Get total number of trades."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM trades')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_recent_trades(self, hours: int = 1) -> pd.DataFrame:
        """Get trades from the last N hours."""
        conn = self._get_connection()
        query = '''
            SELECT * FROM trades 
            WHERE entry_time >= datetime('now', ?)
            ORDER BY entry_time DESC
        '''
        df = pd.read_sql_query(query, conn, params=[f'-{hours} hours'])
        conn.close()
        return df
    
    # ============================================
    # USER BEHAVIOR OPERATIONS
    # ============================================
    
    def log_behavior(self, event_type: str, event_data: str = None,
                     session: str = None, notes: str = None) -> int:
        """Log a user behavior event."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_behavior (event_type, event_data, session, notes)
            VALUES (?, ?, ?, ?)
        ''', (event_type, event_data, session, notes))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id
    
    def get_behavior_history(self, event_type: str = None, limit: int = 100) -> pd.DataFrame:
        """Get user behavior history."""
        conn = self._get_connection()
        query = 'SELECT * FROM user_behavior'
        params = []
        
        if event_type:
            query += ' WHERE event_type = ?'
            params.append(event_type)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    # ============================================
    # VIOLATION OPERATIONS
    # ============================================
    
    def log_violation(self, violation_type: str, description: str = None,
                      trade_id: int = None) -> int:
        """Log a rule violation."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO violations (violation_type, description, trade_id)
            VALUES (?, ?, ?)
        ''', (violation_type, description, trade_id))
        
        violation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return violation_id
    
    def get_violations(self, resolved: bool = None, limit: int = 50) -> pd.DataFrame:
        """Get violation history."""
        conn = self._get_connection()
        query = 'SELECT * FROM violations'
        params = []
        
        if resolved is not None:
            query += ' WHERE resolved = ?'
            params.append(resolved)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    # ============================================
    # BALANCE OPERATIONS
    # ============================================
    
    def update_balance(self, new_balance: float, change_amount: float = 0,
                       reason: str = None) -> None:
        """Update account balance and log the change."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO balance_history (balance, change_amount, change_reason)
            VALUES (?, ?, ?)
        ''', (new_balance, change_amount, reason))
        
        conn.commit()
        conn.close()
    
    def get_current_balance(self) -> float:
        """Get the current account balance."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM balance_history ORDER BY timestamp DESC LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return config.SIMULATION_CONFIG['initial_balance']
    
    def get_balance_history(self, limit: int = 100) -> pd.DataFrame:
        """Get balance history."""
        conn = self._get_connection()
        df = pd.read_sql_query(
            'SELECT * FROM balance_history ORDER BY timestamp DESC LIMIT ?',
            conn, params=[limit]
        )
        conn.close()
        return df
    
    # ============================================
    # STATISTICS & ANALYTICS
    # ============================================
    
    def get_performance_stats(self, asset: str = None, days: int = 30) -> Dict[str, Any]:
        """Get performance statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as best_trade,
                MIN(pnl) as worst_trade,
                AVG(strategy_score) as avg_score
            FROM trades
            WHERE entry_time >= datetime('now', ?)
        '''
        params = [f'-{days} days']
        
        if asset:
            query += ' AND asset = ?'
            params.append(asset)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            total = result['total_trades'] or 0
            wins = result['wins'] or 0
            return {
                'total_trades': total,
                'wins': wins,
                'losses': result['losses'] or 0,
                'win_rate': (wins / total * 100) if total > 0 else 0,
                'total_pnl': result['total_pnl'] or 0,
                'avg_pnl': result['avg_pnl'] or 0,
                'best_trade': result['best_trade'] or 0,
                'worst_trade': result['worst_trade'] or 0,
                'avg_score': result['avg_score'] or 0
            }
        return {}
    
    def get_hourly_performance(self) -> pd.DataFrame:
        """Get performance breakdown by hour of day."""
        conn = self._get_connection()
        query = '''
            SELECT 
                strftime('%H', entry_time) as hour,
                COUNT(*) as trades,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                AVG(pnl) as avg_pnl
            FROM trades
            GROUP BY strftime('%H', entry_time)
            ORDER BY hour
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_session_performance(self) -> pd.DataFrame:
        """Get performance breakdown by trading session."""
        conn = self._get_connection()
        query = '''
            SELECT 
                session,
                COUNT(*) as trades,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl,
                AVG(strategy_score) as avg_score
            FROM trades
            WHERE session IS NOT NULL
            GROUP BY session
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df


# Singleton instance
_db_instance = None

def get_database() -> Database:
    """Get or create database singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
