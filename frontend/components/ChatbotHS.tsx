'use client';

import { useState, useRef, useEffect } from 'react';
import { sendChatMessage, type ChatMessage } from '@/lib/api';

export default function ChatbotHS() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMessage: ChatMessage = {
            role: 'user',
            content: input.trim(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await sendChatMessage({ messages: [...messages, userMessage] });
            const assistantMessage: ChatMessage = {
                role: 'assistant',
                content: response.response,
            };
            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage: ChatMessage = {
                role: 'assistant',
                content: 'Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta de nuevo.',
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="space-y-8 animate-fade-in">
            {/* Header */}
            <div className="glass rounded-3xl p-8 shadow-premium hover-lift">
                <div className="flex items-center gap-4 mb-3">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center shadow-glow">
                        <span className="text-3xl">💬</span>
                    </div>
                    <div>
                        <h2 className="text-4xl font-bold text-gradient">Chatbot HS</h2>
                        <p className="text-slate-600 mt-1">Asistente IA especializado en Hidradenitis Supurativa</p>
                    </div>
                </div>
            </div>

            {/* Chat Container */}
            <div className="glass rounded-3xl shadow-premium overflow-hidden flex flex-col" style={{ height: '600px' }}>
                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
                    {messages.length === 0 && (
                        <div className="h-full flex items-center justify-center text-center">
                            <div className="animate-scale-in">
                                <div className="text-7xl mb-4 animate-bounce">👋</div>
                                <h3 className="text-2xl font-bold text-slate-700 mb-2">¡Hola! Soy tu asistente IA</h3>
                                <p className="text-slate-500 max-w-md">
                                    Pregúntame cualquier cosa sobre Hidradenitis Supurativa y te ayudaré con información científica.
                                </p>
                            </div>
                        </div>
                    )}

                    {messages.map((msg, idx) => (
                        <div
                            key={idx}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-in-up`}
                        >
                            <div
                                className={`
                                    max-w-[75%] px-6 py-4 rounded-2xl shadow-md
                                    ${msg.role === 'user'
                                        ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white'
                                        : 'glass border border-slate-200'
                                    }
                                `}
                            >
                                <div className="flex items-start gap-3">
                                    <div className={`
                                        w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
                                        ${msg.role === 'user' ? 'bg-white/20' : 'bg-gradient-to-br from-purple-400 to-pink-500'}
                                    `}>
                                        <span className="text-lg">{msg.role === 'user' ? '👤' : '🤖'}</span>
                                    </div>
                                    <p className={`text-sm leading-relaxed ${msg.role === 'user' ? 'text-white' : 'text-slate-700'}`}>
                                        {msg.content}
                                    </p>
                                </div>
                            </div>
                        </div>
                    ))}

                    {loading && (
                        <div className="flex justify-start animate-scale-in">
                            <div className="glass border border-slate-200 px-6 py-4 rounded-2xl shadow-md max-w-[75%]">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center">
                                        <span className="text-lg">🤖</span>
                                    </div>
                                    <div className="flex gap-2">
                                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                        <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="border-t border-slate-200 p-6 bg-white/50">
                    <div className="flex gap-3">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Escribe tu pregunta sobre Hidradenitis Supurativa..."
                            className="flex-1 px-4 py-3 rounded-2xl border-2 border-slate-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all outline-none resize-none"
                            rows={2}
                            disabled={loading}
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || loading}
                            className={`
                                px-8 py-3 rounded-2xl font-bold transition-all duration-300 flex items-center gap-2
                                ${!input.trim() || loading
                                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                                    : 'bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-glow hover:shadow-premium hover:scale-105'
                                }
                            `}
                        >
                            <span className="text-xl">🚀</span>
                            <span>Enviar</span>
                        </button>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">
                        Presiona <kbd className="px-2 py-1 bg-slate-200 rounded text-slate-700 font-mono">Enter</kbd> para enviar,
                        <kbd className="px-2 py-1 bg-slate-200 rounded text-slate-700 font-mono ml-1">Shift+Enter</kbd> para nueva línea
                    </p>
                </div>
            </div>
        </div>
    );
}
