// API Service for communicating with FastAPI backend
import axios, { AxiosInstance } from 'axios';

// Fix: Browser needs localhost, Server needs docker internal URL
const getBaseUrl = () => {
    if (typeof window !== 'undefined') {
        return 'http://localhost:8000';
    }
    return process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
};

const baseURL = getBaseUrl();

const apiClient: AxiosInstance = axios.create({
    baseURL: baseURL,
    timeout: 900000, // 15 minutes for long-running validations
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface Message {
    role: 'system' | 'user' | 'assistant';
    content: string;
}

export interface ChatRequest {
    messages: Message[];
    topic?: string;
}

export interface ChatResponse {
    reply: string;
}

export interface ClaimValidationResult {
    where: string;
    text: string;
    status: 'green' | 'yellow' | 'red';
    best_score: number;
    best_verdict: string;
    best_title: string;
    best_url: string | null;
    ranked: any[];
    timings_ms: Record<string, number>;
}

export interface PPTXValidationResponse {
    file_name: string;
    total_claims: number;
    results: ClaimValidationResult[];
    thresholds: {
        green: number;
        yellow: number;
    };
    annotated_pptx_b64?: string;
    annotated_file_name?: string;
    error?: string;
}

export interface TextValidationParams {
    claim_text: string;
    slide_title?: string;
    slide_excerpt?: string;
    topk?: number;
    mock_llm?: boolean;
}

// Chat endpoint
export const sendChatMessage = async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/api/chat', request);
    return response.data;
};

// PPTX validation endpoint
export const validatePPTX = async (
    file: File,
    topk: number = 8,
    thr_green: number = 0.82,
    thr_yellow: number = 0.70,
    render_ppt: boolean = true
): Promise<PPTXValidationResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<PPTXValidationResponse>(
        '/api/claims/validate-ppt',
        formData,
        {
            params: {
                topk,
                thr_green,
                thr_yellow,
                render_ppt,
            },
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        }
    );

    return response.data;
};

// Text validation endpoint
export const validateText = async (params: TextValidationParams): Promise<any> => {
    const response = await apiClient.get('/api/claims/validate', { params });
    return response.data;
};

// Helper to download base64 file
export const downloadBase64File = (base64: string, filename: string, mimeType: string) => {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);

    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }

    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
};

export default apiClient;
