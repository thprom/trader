"""
MarketSense AI - AI Decision Engine
Machine learning-based trade probability prediction and decision support.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import pickle
import os
import json

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

import config
from database import get_database


class AIDecisionEngine:
    """AI-powered decision engine for trade probability prediction."""
    
    def __init__(self):
        self.config = config.AI_CONFIG
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = os.path.join(os.path.dirname(__file__), 'models', 'trade_model.pkl')
        self.scaler_path = os.path.join(os.path.dirname(__file__), 'models', 'scaler.pkl')
        self.feature_names = []
        self.is_trained = False
        self.model_metrics = {}
        
        # Ensure models directory exists
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        # Try to load existing model
        self._load_model()
    
    def _load_model(self) -> bool:
        """Load existing model from disk."""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data['model']
                    self.feature_names = model_data['feature_names']
                    self.model_metrics = model_data.get('metrics', {})
                
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                self.is_trained = True
                return True
        except Exception as e:
            print(f"Error loading model: {e}")
        return False
    
    def _save_model(self) -> bool:
        """Save model to disk."""
        try:
            model_data = {
                'model': self.model,
                'feature_names': self.feature_names,
                'metrics': self.model_metrics,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            return True
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
    
    def prepare_features(self, signals: Dict[str, Any]) -> np.ndarray:
        """Convert trading signals to feature vector."""
        features = []
        
        # RSI features
        rsi_data = signals.get('rsi', {})
        features.append(rsi_data.get('value', 50))
        features.append(rsi_data.get('strength', 0.5))
        features.append(1 if rsi_data.get('signal') == 'BULLISH' else 
                       -1 if rsi_data.get('signal') == 'BEARISH' else 0)
        
        # EMA features
        ema_data = signals.get('ema', {})
        features.append(ema_data.get('strength', 0.5))
        features.append(1 if ema_data.get('signal') == 'BULLISH' else 
                       -1 if ema_data.get('signal') == 'BEARISH' else 0)
        features.append(1 if ema_data.get('crossover') == 'BULLISH_CROSS' else 
                       -1 if ema_data.get('crossover') == 'BEARISH_CROSS' else 0)
        
        # MACD features
        macd_data = signals.get('macd', {})
        features.append(macd_data.get('histogram', 0))
        features.append(macd_data.get('strength', 0.5))
        features.append(1 if macd_data.get('trend') == 'BULLISH' else 
                       -1 if macd_data.get('trend') == 'BEARISH' else 0)
        
        # Bollinger features
        bb_data = signals.get('bollinger', {})
        features.append(bb_data.get('percent', 0.5))
        features.append(bb_data.get('width', 0))
        features.append(1 if bb_data.get('signal') == 'BULLISH' else 
                       -1 if bb_data.get('signal') == 'BEARISH' else 0)
        
        # Candle features
        candle_data = signals.get('candle', {})
        features.append(1 if candle_data.get('type') == 'BULLISH' else 
                       -1 if candle_data.get('type') == 'BEARISH' else 0)
        
        # Pattern encoding
        pattern = candle_data.get('pattern', 'NONE')
        pattern_score = {
            'HAMMER': 1, 'INVERTED_HAMMER': 0.5, 'MARUBOZU_BULLISH': 1,
            'MARUBOZU_BEARISH': -1, 'DOJI': 0, 'SPINNING_TOP': 0, 'NONE': 0
        }.get(pattern, 0)
        features.append(pattern_score)
        
        # Overall bias
        bias_data = signals.get('overall_bias', {})
        features.append(bias_data.get('confidence', 0.5))
        features.append(bias_data.get('bullish_signals', 0))
        features.append(bias_data.get('bearish_signals', 0))
        
        return np.array(features).reshape(1, -1)
    
    def train_model(self, force: bool = False) -> Dict[str, Any]:
        """Train the AI model using historical trade data."""
        db = get_database()
        trades_df = db.get_trades(limit=10000)
        
        if trades_df.empty or len(trades_df) < self.config['min_training_samples']:
            return {
                'success': False,
                'message': f"Insufficient training data. Need at least {self.config['min_training_samples']} trades.",
                'current_samples': len(trades_df)
            }
        
        # Prepare training data
        X = []
        y = []
        
        for _, trade in trades_df.iterrows():
            if trade['indicators_snapshot'] and trade['outcome']:
                try:
                    signals = json.loads(trade['indicators_snapshot'])
                    features = self.prepare_features(signals).flatten()
                    X.append(features)
                    y.append(1 if trade['outcome'] == 'WIN' else 0)
                except:
                    continue
        
        if len(X) < self.config['min_training_samples']:
            return {
                'success': False,
                'message': f"Insufficient valid training samples. Need at least {self.config['min_training_samples']}.",
                'valid_samples': len(X)
            }
        
        X = np.array(X)
        y = np.array(y)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        # Train model
        if self.config['model_type'] == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
        else:
            self.model = LogisticRegression(random_state=42)
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        
        self.model_metrics = {
            'accuracy': round(accuracy_score(y_test, y_pred), 4),
            'precision': round(precision_score(y_test, y_pred, zero_division=0), 4),
            'recall': round(recall_score(y_test, y_pred, zero_division=0), 4),
            'f1_score': round(f1_score(y_test, y_pred, zero_division=0), 4),
            'training_samples': len(X),
            'trained_at': datetime.now().isoformat()
        }
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=5)
        self.model_metrics['cv_mean'] = round(cv_scores.mean(), 4)
        self.model_metrics['cv_std'] = round(cv_scores.std(), 4)
        
        # Save model
        self.feature_names = [
            'rsi_value', 'rsi_strength', 'rsi_signal',
            'ema_strength', 'ema_signal', 'ema_crossover',
            'macd_histogram', 'macd_strength', 'macd_trend',
            'bb_percent', 'bb_width', 'bb_signal',
            'candle_type', 'candle_pattern',
            'bias_confidence', 'bullish_signals', 'bearish_signals'
        ]
        
        self._save_model()
        self.is_trained = True
        
        # Log metrics to database
        db.log_behavior('model_trained', json.dumps(self.model_metrics))
        
        return {
            'success': True,
            'metrics': self.model_metrics
        }
    
    def predict_trade(self, signals: Dict[str, Any], direction: str = None) -> Dict[str, Any]:
        """Predict trade probability and generate recommendation."""
        
        # Default response if model not trained
        if not self.is_trained or self.model is None:
            return self._generate_rule_based_prediction(signals, direction)
        
        try:
            features = self.prepare_features(signals)
            features_scaled = self.scaler.transform(features)
            
            # Get probability
            probabilities = self.model.predict_proba(features_scaled)[0]
            win_probability = probabilities[1] if len(probabilities) > 1 else 0.5
            
            # Adjust for direction if specified
            bias = signals.get('overall_bias', {})
            bias_direction = bias.get('direction', 'NEUTRAL')
            
            if direction:
                if (direction == 'CALL' and bias_direction == 'BEARISH') or \
                   (direction == 'PUT' and bias_direction == 'BULLISH'):
                    win_probability *= 0.8  # Reduce probability for counter-trend trades
            
            # Generate recommendation
            recommendation = self._generate_recommendation(win_probability, signals)
            
            # Calculate risk level
            risk_level = self._calculate_risk_level(win_probability, signals)
            
            return {
                'probability': round(win_probability * 100, 1),
                'confidence': round(self.model_metrics.get('accuracy', 0.5) * 100, 1),
                'recommendation': recommendation,
                'risk_level': risk_level,
                'model_version': self.model_metrics.get('trained_at', 'unknown'),
                'training_samples': self.model_metrics.get('training_samples', 0),
                'direction_alignment': self._check_direction_alignment(direction, bias_direction)
            }
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return self._generate_rule_based_prediction(signals, direction)
    
    def _generate_rule_based_prediction(self, signals: Dict[str, Any], 
                                        direction: str = None) -> Dict[str, Any]:
        """Generate prediction using rule-based logic when ML model unavailable."""
        bias = signals.get('overall_bias', {})
        bullish = bias.get('bullish_signals', 0)
        bearish = bias.get('bearish_signals', 0)
        total = bias.get('total_signals', 5)
        
        # Calculate base probability
        if direction == 'CALL':
            probability = (bullish / total) * 100 if total > 0 else 50
        elif direction == 'PUT':
            probability = (bearish / total) * 100 if total > 0 else 50
        else:
            probability = max(bullish, bearish) / total * 100 if total > 0 else 50
        
        # Adjust for signal strength
        rsi_strength = signals.get('rsi', {}).get('strength', 0.5)
        ema_strength = signals.get('ema', {}).get('strength', 0.5)
        avg_strength = (rsi_strength + ema_strength) / 2
        
        probability = probability * (0.5 + avg_strength * 0.5)
        probability = min(max(probability, 20), 80)  # Clamp between 20-80%
        
        recommendation = self._generate_recommendation(probability / 100, signals)
        risk_level = self._calculate_risk_level(probability / 100, signals)
        
        return {
            'probability': round(probability, 1),
            'confidence': 50.0,  # Lower confidence for rule-based
            'recommendation': recommendation,
            'risk_level': risk_level,
            'model_version': 'rule_based',
            'training_samples': 0,
            'note': 'Using rule-based prediction. Train model with more data for ML predictions.'
        }
    
    def _generate_recommendation(self, probability: float, signals: Dict[str, Any]) -> str:
        """Generate trade recommendation based on probability and signals."""
        threshold = self.config['confidence_threshold']
        
        # Check for trap signals
        trap_detected = self._detect_trap_signals(signals)
        
        if trap_detected:
            return 'AVOID'
        
        if probability >= 0.7:
            return 'ENTER'
        elif probability >= threshold:
            return 'WAIT'  # Marginal setup
        else:
            return 'AVOID'
    
    def _calculate_risk_level(self, probability: float, signals: Dict[str, Any]) -> str:
        """Calculate risk level for the trade setup."""
        # Base risk on probability
        if probability >= 0.7:
            base_risk = 'LOW'
        elif probability >= 0.55:
            base_risk = 'MEDIUM'
        else:
            base_risk = 'HIGH'
        
        # Adjust for volatility
        bb_width = signals.get('bollinger', {}).get('width', 0)
        if bb_width > 0.03:  # High volatility
            if base_risk == 'LOW':
                base_risk = 'MEDIUM'
            elif base_risk == 'MEDIUM':
                base_risk = 'HIGH'
        
        return base_risk
    
    def _detect_trap_signals(self, signals: Dict[str, Any]) -> bool:
        """Detect potential marketing trap patterns."""
        trap_config = config.TRAP_DETECTION_CONFIG
        
        # Check for "too perfect" setup
        bias = signals.get('overall_bias', {})
        total_signals = bias.get('total_signals', 5)
        max_aligned = max(bias.get('bullish_signals', 0), bias.get('bearish_signals', 0))
        
        if total_signals > 0:
            alignment_ratio = max_aligned / total_signals
            if alignment_ratio >= trap_config['perfect_setup_threshold']:
                return True
        
        # Check for late entry (price near Bollinger bands)
        bb_percent = signals.get('bollinger', {}).get('percent', 0.5)
        if bb_percent > trap_config['late_entry_threshold'] or bb_percent < (1 - trap_config['late_entry_threshold']):
            return True
        
        return False
    
    def _check_direction_alignment(self, trade_direction: str, bias_direction: str) -> str:
        """Check if trade direction aligns with market bias."""
        if not trade_direction:
            return 'N/A'
        
        if (trade_direction == 'CALL' and bias_direction == 'BULLISH') or \
           (trade_direction == 'PUT' and bias_direction == 'BEARISH'):
            return 'ALIGNED'
        elif bias_direction == 'NEUTRAL':
            return 'NEUTRAL'
        else:
            return 'COUNTER_TREND'
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the trained model."""
        if not self.is_trained or self.model is None:
            return {}
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            return dict(zip(self.feature_names, [round(x, 4) for x in importances]))
        elif hasattr(self.model, 'coef_'):
            importances = np.abs(self.model.coef_[0])
            return dict(zip(self.feature_names, [round(x, 4) for x in importances]))
        
        return {}
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get current model status and metrics."""
        return {
            'is_trained': self.is_trained,
            'model_type': self.config['model_type'],
            'metrics': self.model_metrics,
            'feature_importance': self.get_feature_importance(),
            'min_training_samples': self.config['min_training_samples'],
            'confidence_threshold': self.config['confidence_threshold']
        }


# Singleton instance
_ai_engine = None

def get_ai_engine() -> AIDecisionEngine:
    """Get or create AI engine singleton."""
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIDecisionEngine()
    return _ai_engine
