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
    compliance_status?: 'pass' | 'fail';
    compliance_reason?: string;
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

export interface PodcastResponse {
    script: Array<{ speaker: string; text: string }>;
    audio_base64: string;
    file_name: string;
}

// Podcast generation endpoint
export const generatePodcast = async (file: File): Promise<PodcastResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<PodcastResponse>(
        '/api/generate/podcast',
        formData,
        {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 300000, // 5 minutes for generation
        }
    );

    return response.data;
};

export interface SummaryResponse {
    summary: string;
    file_name: string;
}

export const generateSummary = async (file: File): Promise<SummaryResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<SummaryResponse>(
        '/api/generate/summary',
        formData,
        {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 300000,
        }
    );

    return response.data;
};

export const generateSlides = async (text: string | null, file: File | null, numSlides: number = 5): Promise<Blob> => {
    const formData = new FormData();
    if (text) formData.append('text', text);
    if (file) formData.append('file', file);
    formData.append('num_slides', numSlides.toString());

    const response = await apiClient.post(
        '/api/generate/slides',
        formData,
        {
            responseType: 'blob', // Importante para recibir archivos binarios
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 300000,
        }
    );
    return response.data;
};

export default apiClient;
