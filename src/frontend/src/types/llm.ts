/**
 * Types for LLM/AI features configuration and responses
 */

export interface LLMConfig {
    enabled: boolean;
    endpoint: string | null;
    system_prompt: string | null;
    disclaimer_text: string;
}

export interface LLMAnalysisResult {
    request_id: string;
    asset_id: string;
    analysis_summary: string;
    model_used: string | null;
    timestamp: string;
    // Security metadata
    phase1_passed: boolean;
    render_as_markdown: boolean;
}

export interface LLMConsentState {
    accepted: boolean;
    timestamp: string;
    config_version?: string; // Track config changes
}
