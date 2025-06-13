from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

Base = declarative_base()


class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    call_sid = Column(String(100), unique=True, nullable=False)
    caller_phone = Column(String(20))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    status = Column(String(20), default='active')
    summary = Column(Text)
    
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, call_sid='{self.call_sid}', status='{self.status}')>"


class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    speaker = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    audio_duration = Column(Float)
    
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, speaker='{self.speaker}', content='{self.content[:50]}...')>"


class DatabaseManager:
    def __init__(self, database_url=None):
        if database_url is None:
            database_url = f"sqlite:///{os.path.join(os.getcwd(), 'conversations.db')}"
        
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def create_conversation(self, call_sid, caller_phone=None):
        """create a new conversation record"""
        conversation = Conversation(
            call_sid=call_sid,
            caller_phone=caller_phone,
            start_time=datetime.utcnow()
        )
        self.session.add(conversation)
        self.session.commit()
        return conversation
    
    def add_message(self, conversation_id, speaker, content, audio_duration=None):
        """add a message to a conversation"""
        message = Message(
            conversation_id=conversation_id,
            speaker=speaker,
            content=content,
            timestamp=datetime.utcnow(),
            audio_duration=audio_duration
        )
        self.session.add(message)
        self.session.commit()
        return message
    
    def end_conversation(self, conversation_id, status='completed'):
        """mark a conversation as ended"""
        conversation = self.session.query(Conversation).filter_by(id=conversation_id).first()
        if conversation:
            conversation.end_time = datetime.utcnow()
            conversation.status = status
            if conversation.start_time:
                duration = conversation.end_time - conversation.start_time
                conversation.duration_seconds = duration.total_seconds()
            self.session.commit()
        return conversation
    
    def get_conversation_by_call_sid(self, call_sid):
        """get conversation by twilio call sid"""
        return self.session.query(Conversation).filter_by(call_sid=call_sid).first()
    
    def get_all_conversations(self, limit=50):
        """get all conversations, most recent first"""
        return self.session.query(Conversation).order_by(Conversation.start_time.desc()).limit(limit).all()
    
    def get_conversation_with_messages(self, conversation_id):
        """get a conversation with all its messages"""
        return self.session.query(Conversation).filter_by(id=conversation_id).first()
    
    def update_conversation_summary(self, conversation_id, summary):
        """update the summary for a conversation"""
        conversation = self.session.query(Conversation).filter_by(id=conversation_id).first()
        if conversation:
            conversation.summary = summary
            self.session.commit()
        return conversation
    
    def close(self):
        """close the database session"""
        self.session.close() 