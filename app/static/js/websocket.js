class WebSocketManager {
    constructor() {
        this.socket = null;
        this.subscriptions = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }
    
    connect() {
        if (this.socket && this.socket.connected) {
            return;
        }
        
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        });
        
        this.socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            this.attemptReconnect();
        });
        
        this.socket.on('error', (error) => {
            console.error('WebSocket error:', error);
        });
        
        // Set up subscription handlers
        this.subscriptions.forEach((callback, event) => {
            this.socket.on(event, callback);
        });
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Reconnect attempt ${this.reconnectAttempts}`);
                this.connect();
            }, 2000 * this.reconnectAttempts);
        }
    }
    
    subscribe(event, callback) {
        this.subscriptions.set(event, callback);
        if (this.socket && this.socket.connected) {
            this.socket.on(event, callback);
        }
    }
    
    unsubscribe(event) {
        this.subscriptions.delete(event);
        if (this.socket) {
            this.socket.off(event);
        }
    }
    
    emit(event, data) {
        if (this.socket && this.socket.connected) {
            this.socket.emit(event, data);
        }
    }
    
    joinRoom(room) {
        this.emit('join', {room: room});
    }
    
    leaveRoom(room) {
        this.emit('leave', {room: room});
    }
}

const wsManager = new WebSocketManager();
