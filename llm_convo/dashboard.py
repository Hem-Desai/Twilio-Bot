from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import os
from llm_convo.database import DatabaseManager, Conversation, Message
from llm_convo.conversation_summarizer import create_summary_service


class ConversationDashboard:
    def __init__(self, database_url=None, port=5000):
        self.app = Flask(__name__, template_folder='templates', static_folder='static')
        self.port = port
        
        # Initialize database
        self.db_manager = DatabaseManager(database_url)
        
        # Initialize summary service
        try:
            self.summary_service = create_summary_service(database_url)
        except Exception as e:
            print(f"⚠️ Summary service not available: {e}")
            self.summary_service = None
        
        # Setup routes
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')
        
        @self.app.route('/api/conversations')
        def get_conversations():
            try:
                limit = request.args.get('limit', 50, type=int)
                conversations = self.db_manager.get_all_conversations(limit=limit)
                
                result = []
                for conv in conversations:
                    conv_data = {
                        'id': conv.id,
                        'call_sid': conv.call_sid,
                        'caller_phone': conv.caller_phone,
                        'start_time': conv.start_time.isoformat() if conv.start_time else None,
                        'end_time': conv.end_time.isoformat() if conv.end_time else None,
                        'duration_seconds': conv.duration_seconds,
                        'status': conv.status,
                        'message_count': len(conv.messages),
                        'summary': conv.summary,
                        'has_summary': bool(conv.summary)
                    }
                    result.append(conv_data)
                
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/conversations/<int:conversation_id>')
        def get_conversation_details(conversation_id):
            try:
                conversation = self.db_manager.get_conversation_with_messages(conversation_id)
                if not conversation:
                    return jsonify({'error': 'Conversation not found'}), 404
                
                messages = []
                for msg in conversation.messages:
                    msg_data = {
                        'id': msg.id,
                        'speaker': msg.speaker,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                        'audio_duration': msg.audio_duration
                    }
                    messages.append(msg_data)
                
                result = {
                    'id': conversation.id,
                    'call_sid': conversation.call_sid,
                    'caller_phone': conversation.caller_phone,
                    'start_time': conversation.start_time.isoformat() if conversation.start_time else None,
                    'end_time': conversation.end_time.isoformat() if conversation.end_time else None,
                    'duration_seconds': conversation.duration_seconds,
                    'status': conversation.status,
                    'summary': conversation.summary,
                    'has_summary': bool(conversation.summary),
                    'messages': messages
                }
                
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stats')
        def get_stats():
            try:
                # Get basic statistics
                all_conversations = self.db_manager.get_all_conversations(limit=1000)
                
                total_conversations = len(all_conversations)
                active_conversations = len([c for c in all_conversations if c.status == 'active'])
                completed_conversations = len([c for c in all_conversations if c.status == 'completed'])
                
                # Calculate average duration
                completed_with_duration = [c for c in all_conversations if c.duration_seconds is not None]
                avg_duration = sum(c.duration_seconds for c in completed_with_duration) / len(completed_with_duration) if completed_with_duration else 0
                
                # Get conversations from last 24 hours
                yesterday = datetime.utcnow() - timedelta(days=1)
                recent_conversations = [c for c in all_conversations if c.start_time and c.start_time > yesterday]
                
                stats = {
                    'total_conversations': total_conversations,
                    'active_conversations': active_conversations,
                    'completed_conversations': completed_conversations,
                    'average_duration_seconds': round(avg_duration, 2),
                    'conversations_last_24h': len(recent_conversations)
                }
                
                return jsonify(stats)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/conversation/<int:conversation_id>')
        def conversation_detail(conversation_id):
            return render_template('conversation_detail.html', conversation_id=conversation_id)
        
        @self.app.route('/api/conversations/<int:conversation_id>/summary', methods=['POST'])
        def generate_summary(conversation_id):
            """Generate a summary for a specific conversation"""
            if not self.summary_service:
                return jsonify({'error': 'Summary service not available'}), 503
            
            try:
                summary = self.summary_service.generate_and_save_summary(conversation_id)
                if summary:
                    return jsonify({
                        'success': True,
                        'summary': summary,
                        'conversation_id': conversation_id
                    })
                else:
                    return jsonify({'error': 'Failed to generate summary'}), 500
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/summaries/batch', methods=['POST'])
        def batch_generate_summaries():
            """Generate summaries for all conversations without summaries"""
            if not self.summary_service:
                return jsonify({'error': 'Summary service not available'}), 503
            
            try:
                limit = request.json.get('limit', 50) if request.json else 50
                stats = self.summary_service.batch_generate_summaries(limit=limit)
                return jsonify({
                    'success': True,
                    'stats': stats
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/conversations/<int:conversation_id>/summary', methods=['GET'])
        def get_summary(conversation_id):
            """Get the summary for a specific conversation"""
            if not self.summary_service:
                return jsonify({'error': 'Summary service not available'}), 503
            
            try:
                summary = self.summary_service.get_summary(conversation_id)
                return jsonify({
                    'conversation_id': conversation_id,
                    'summary': summary,
                    'has_summary': bool(summary)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def run(self, debug=True):
        self.app.run(host='0.0.0.0', port=self.port, debug=debug)


def create_dashboard_templates():
    """Create the HTML templates for the dashboard"""
    
    # Create templates directory
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # Create static directory
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    os.makedirs(static_dir, exist_ok=True)
    
    return templates_dir, static_dir 