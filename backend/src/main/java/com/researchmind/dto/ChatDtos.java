package com.researchmind.dto;

import java.util.List;

public class ChatDtos {

    public static class ChatRequest {
        public Long conversationId; // null = start a new conversation
        public String message;
        public List<Long> documentIds;
    }

    public static class Citation {
        public int index;
        public String document;
        public int page;
        public String section;
        public double rerankScore;
    }

    public static class ChatResponse {
        public Long conversationId;
        public String answer;
        public List<Citation> citations;
        public boolean grounded;
        public Double faithfulnessScore;
        public int latencyMs;
    }
}
