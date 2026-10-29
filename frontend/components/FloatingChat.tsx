'use client';

import { useState, useRef, useEffect } from 'react';
import { sendChatMessage, type Message } from '@/lib/api';

interface FloatingChatProps {
    context: 'validator' | 'generator';
    initialOpen?: boolean;
}

export default function FloatingChat({ context, initialOpen = false }: FloatingChatProps) {
    const [isOpen, setIsOpen] = useState(initialOpen);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [hasNewMessage, setHasNewMessage] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const contextTitles = {
        validator: 'Asistente de Validación',
        generator: 'Asistente de Generación',
    };

    const contextPlaceholders = {
        validator: '¿Necesitas ayuda validando claims?',
        generator: '¿Cómo puedo ayudarte a generar material?',
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        // Show notification badge when new assistant message arrives and chat is closed
        if (!isOpen && messages.length > 0 && messages[messages.length - 1].role === 'assistant') {
            setHasNewMessage(true);
        }
    }, [messages, isOpen]);

    useEffect(() => {
        // Clear notification when chat is opened
        if (isOpen) {
            setHasNewMessage(false);
        }
    }, [isOpen]);

    useEffect(() => {
        // Close chat on Escape key
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) {
                setIsOpen(false);
            }
        };
        window.addEventListener('keydown', handleEscape);
        return () => window.removeEventListener('keydown', handleEscape);
    }, [isOpen]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMessage: Message = {
            role: 'user',
            content: input.trim(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        // Prepare messages for API
        const apiMessages = [...messages, userMessage];

        try {
            // Removed topic parameter to fix 500 error
            const response = await sendChatMessage({
                messages: apiMessages,
            });

            const assistantMessage: Message = {
                role: 'assistant',
                content: response.reply,
            };
            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error: any) {
            console.error('Error sending message:', error);
            if (error.response) {
                console.error('Backend error data:', error.response.data);
                console.error('Backend error status:', error.response.status);
            }
            const errorDetail = error.response?.data?.detail || error.message || 'Error desconocido';
            const errorMessage: Message = {
                role: 'assistant',
                content: `Error: ${errorDetail}. Por favor, intenta de nuevo.`,
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
        <>
            {/* Floating Button */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="fixed bottom-8 right-8 w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full shadow-glow hover:shadow-premium hover:scale-110 transition-all duration-300 z-50 flex items-center justify-center group animate-scale-in"
                    aria-label="Abrir chat"
                >
                    <span className="text-3xl group-hover:scale-110 transition-transform">💬</span>
                    {hasNewMessage && (
                        <div className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full border-2 border-white animate-pulse shadow-glow"></div>
                    )}
                </button>
            )}

            {/* Floating Chat Panel */}
            {isOpen && (
                <div className="fixed bottom-0 right-0 w-full sm:w-[400px] h-[600px] sm:h-[700px] sm:bottom-8 sm:right-8 z-50 animate-slide-in-right">
                    <div className="glass rounded-t-3xl sm:rounded-3xl shadow-premium h-full flex flex-col overflow-hidden border border-white/20">
                        {/* Header */}
                        <div className="bg-gradient-to-r from-purple-500 to-pink-600 p-4 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                                    <span className="text-2xl">🤖</span>
                                </div>
                                <div>
                                    <h3 className="font-bold text-white">{contextTitles[context]}</h3>
                                    <p className="text-xs text-white/80">Siempre disponible para ayudarte</p>
                                </div>
                            </div>
                            <button
                                onClick={() => setIsOpen(false)}
                                className="w-8 h-8 rounded-full bg-white/20 hover:bg-white/30 transition-colors flex items-center justify-center"
                                aria-label="Cerrar chat"
                            >
                                <span className="text-white text-xl">✕</span>
                            </button>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-gradient-to-b from-white/50 to-white/30">
                            {messages.length === 0 && (
                                <div className="h-full flex items-center justify-center text-center">
                                    <div className="animate-scale-in">
                                        <div className="text-6xl mb-4 animate-bounce">👋</div>
                                        <h4 className="text-lg font-bold text-slate-700 mb-2">¡Hola!</h4>
                                        <p className="text-sm text-slate-500 max-w-xs">
                                            Soy tu asistente IA especializado en Hidradenitis Supurativa. ¿En qué puedo ayudarte?
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
                                            max-w-[85%] px-4 py-3 rounded-2xl shadow-md
                                            ${msg.role === 'user'
                                                ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white'
                                                : 'glass border border-slate-200'
                                            }
                                        `}
                                    >
                                        <div className="flex items-start gap-2">
                                            <div className={`
                                                w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0
                                                ${msg.role === 'user' ? 'bg-white/20' : 'bg-gradient-to-br from-purple-400 to-pink-500'}
                                            `}>
                                                <span className="text-sm">{msg.role === 'user' ? '👤' : '🤖'}</span>
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
                                    <div className="glass border border-slate-200 px-4 py-3 rounded-2xl shadow-md max-w-[85%]">
                                        <div className="flex items-center gap-2">
                                            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center">
                                                <span className="text-sm">🤖</span>
                                            </div>
                                            <div className="flex gap-1">
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
                        <div className="border-t border-white/20 p-4 bg-white/50">
                            <div className="flex gap-2">
                                <textarea
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    placeholder={contextPlaceholders[context]}
                                    className="flex-1 px-3 py-2 rounded-xl border-2 border-slate-200 focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all outline-none resize-none text-sm"
                                    rows={2}
                                    disabled={loading}
                                />
                                <button
                                    onClick={handleSend}
                                    disabled={!input.trim() || loading}
                                    className={`
                                        px-4 py-2 rounded-xl font-bold transition-all duration-300 flex items-center gap-1 self-end
                                        ${!input.trim() || loading
                                            ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                                            : 'bg-gradient-to-r from-purple-500 to-pink-600 text-white shadow-glow hover:shadow-premium hover:scale-105'
                                        }
                                    `}
                                >
                                    <span className="text-lg">🚀</span>
                                </button>
                            </div>
                            <p className="text-xs text-slate-500 mt-2">
                                <kbd className="px-1.5 py-0.5 bg-slate-200 rounded text-slate-700 font-mono text-xs">Enter</kbd> enviar ·
                                <kbd className="px-1.5 py-0.5 bg-slate-200 rounded text-slate-700 font-mono text-xs ml-1">Esc</kbd> cerrar
                            </p>
                        </div>
                    </div>
                </div>
            )}

            <style jsx>{`
                @keyframes slide-in-right {
                    from {
                        opacity: 0;
                        transform: translateX(100%);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(0);
                    }
                }
                .animate-slide-in-right {
                    animation: slide-in-right 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                }
            `}</style>
        </>
    );
}
