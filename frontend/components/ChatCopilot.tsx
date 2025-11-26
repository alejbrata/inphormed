'use client';

import { useState, useRef, useEffect } from 'react';
import { sendChatMessage, type Message, type PPTXValidationResponse } from '@/lib/api';
import { MessageCircle, X, Send, Bot, User, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ChatCopilotProps {
    context: 'validator' | 'generator';
    initialOpen?: boolean;
    validationContext?: PPTXValidationResponse | null;
}

export default function ChatCopilot({ context, initialOpen = false, validationContext }: ChatCopilotProps) {
    const [isOpen, setIsOpen] = useState(initialOpen);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [hasNewMessage, setHasNewMessage] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Effect to notify user when context is available
    useEffect(() => {
        if (validationContext && messages.length === 0) {
            setHasNewMessage(true);
        }
    }, [validationContext]);

    const contextTitles = {
        validator: 'Medical Copilot',
        generator: 'Content Assistant',
    };

    const contextPlaceholders = {
        validator: 'Pregunta sobre la validación clínica...',
        generator: '¿Qué material necesitas generar?',
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        if (!isOpen && messages.length > 0 && messages[messages.length - 1].role === 'assistant') {
            setHasNewMessage(true);
        }
    }, [messages, isOpen]);

    useEffect(() => {
        if (isOpen) {
            setHasNewMessage(false);
        }
    }, [isOpen]);

    const formatValidationContext = (data: PPTXValidationResponse): string => {
        let ctx = `CONTEXTO DEL ANÁLISIS DE VALIDACIÓN:\n`;
        ctx += `Archivo: ${data.file_name}\n`;
        ctx += `Total Claims: ${data.total_claims}\n\n`;
        ctx += `RESULTADOS DETALLADOS:\n`;

        data.results.forEach((r, i) => {
            ctx += `--- Claim ${i + 1} (${r.where}) ---\n`;
            ctx += `Texto: "${r.text}"\n`;
            ctx += `Estado: ${r.status.toUpperCase()} (Score: ${r.best_score.toFixed(2)})\n`;
            if (r.best_url) {
                ctx += `Evidencia: "${r.best_verdict}"\n`;
                ctx += `Fuente: ${r.best_title}\n`;
            } else {
                ctx += `Evidencia: No encontrada o insuficiente.\n`;
            }
            ctx += `\n`;
        });

        return ctx;
    };

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
        let apiMessages = [...messages, userMessage];

        // Inject context if available and not already present
        if (validationContext) {
            const contextString = formatValidationContext(validationContext);
            const systemMessage: Message = {
                role: 'system',
                content: `Eres un asistente médico experto. Usa el siguiente contexto de validación para responder preguntas sobre la presentación analizada. Si te preguntan por una slide específica, busca en el contexto.\n\n${contextString}`
            };

            // Prepend system message
            apiMessages = [systemMessage, ...apiMessages];
        }

        try {
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
            {/* Floating Toggle Button */}
            <AnimatePresence>
                {!isOpen && (
                    <motion.button
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                        onClick={() => setIsOpen(true)}
                        className="fixed bottom-8 right-8 w-14 h-14 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full shadow-lg shadow-indigo-500/30 flex items-center justify-center z-50 transition-colors"
                    >
                        <MessageCircle className="w-6 h-6" />
                        {hasNewMessage && (
                            <span className="absolute top-0 right-0 w-4 h-4 bg-teal-500 border-2 border-white rounded-full"></span>
                        )}
                    </motion.button>
                )}
            </AnimatePresence>

            {/* Chat Panel */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ x: 100, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: 100, opacity: 0 }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        className="fixed top-24 right-8 bottom-8 w-[400px] z-40 flex flex-col"
                    >
                        <div className="flex-1 flex flex-col bg-white/80 backdrop-blur-xl border border-slate-200 rounded-3xl shadow-2xl overflow-hidden">
                            {/* Header */}
                            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-white/50">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600">
                                        <Sparkles className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-slate-800">{contextTitles[context]}</h3>
                                        <p className="text-xs text-slate-500">AI Powered Assistant</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setIsOpen(false)}
                                    className="p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {/* Messages Area */}
                            <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
                                {messages.length === 0 && (
                                    <div className="h-full flex flex-col items-center justify-center text-center p-6 opacity-60">
                                        <Bot className="w-12 h-12 text-slate-300 mb-4" />
                                        <p className="text-sm text-slate-500">
                                            Hola, soy tu copiloto médico. <br />
                                            Puedo ayudarte a interpretar evidencias o generar contenido.
                                        </p>
                                    </div>
                                )}

                                {messages.map((msg, idx) => (
                                    <motion.div
                                        key={idx}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                                    >
                                        <div className={`
                                            w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
                                            ${msg.role === 'user' ? 'bg-indigo-100 text-indigo-600' : 'bg-teal-100 text-teal-600'}
                                        `}>
                                            {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                                        </div>
                                        <div className={`
                                            max-w-[80%] p-4 rounded-2xl text-sm leading-relaxed
                                            ${msg.role === 'user'
                                                ? 'bg-indigo-600 text-white rounded-tr-none'
                                                : 'bg-white border border-slate-100 text-slate-700 rounded-tl-none shadow-sm'
                                            }
                                        `}>
                                            {msg.content}
                                        </div>
                                    </motion.div>
                                ))}

                                {loading && (
                                    <div className="flex gap-3">
                                        <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center flex-shrink-0">
                                            <Bot className="w-4 h-4" />
                                        </div>
                                        <div className="bg-white border border-slate-100 px-4 py-3 rounded-2xl rounded-tl-none shadow-sm flex gap-1 items-center">
                                            <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></span>
                                            <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce delay-75"></span>
                                            <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce delay-150"></span>
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Input Area */}
                            <div className="p-4 bg-white border-t border-slate-100">
                                <div className="relative">
                                    <textarea
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        onKeyPress={handleKeyPress}
                                        placeholder={contextPlaceholders[context]}
                                        className="w-full pl-4 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all resize-none text-sm"
                                        rows={1}
                                        style={{ minHeight: '46px', maxHeight: '120px' }}
                                    />
                                    <button
                                        onClick={handleSend}
                                        disabled={!input.trim() || loading}
                                        className="absolute right-2 top-2 p-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        <Send className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
