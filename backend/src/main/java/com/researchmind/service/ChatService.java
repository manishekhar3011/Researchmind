package com.researchmind.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.researchmind.dto.ChatDtos.*;
import com.researchmind.entity.Conversation;
import com.researchmind.entity.Message;
import com.researchmind.repository.ConversationRepository;
import com.researchmind.repository.MessageRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

import java.util.List;
import java.util.Map;

@Service
public class ChatService {

    private final ConversationRepository conversationRepository;
    private final MessageRepository messageRepository;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${app.ai-service.base-url}")
    private String aiServiceBaseUrl;

    public ChatService(ConversationRepository conversationRepository,
                        MessageRepository messageRepository,
                        RestTemplate restTemplate) {
        this.conversationRepository = conversationRepository;
        this.messageRepository = messageRepository;
        this.restTemplate = restTemplate;
    }

    public ChatResponse chat(Long userId, ChatRequest request) {
        Conversation conversation = resolveConversation(userId, request.conversationId, request.message);

        Message userMessage = new Message();
        userMessage.setConversationId(conversation.getId());
        userMessage.setRole(Message.Role.USER);
        userMessage.setContent(request.message);
        messageRepository.save(userMessage);

        Map<String, Object> aiRequestBody = Map.of(
                "query", request.message,
                "document_ids", request.documentIds == null ? List.of() : request.documentIds
        );

        @SuppressWarnings("unchecked")
        Map<String, Object> aiResponse = restTemplate.postForObject(
                aiServiceBaseUrl + "/internal/chat", aiRequestBody, Map.class);

        if (aiResponse == null) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI service returned no response");
        }

        String answer = (String) aiResponse.get("answer");
        boolean grounded = Boolean.TRUE.equals(aiResponse.get("grounded"));
        Object faithfulnessRaw = aiResponse.get("faithfulness_score");
        Double faithfulness = faithfulnessRaw == null ? null : ((Number) faithfulnessRaw).doubleValue();
        int latencyMs = ((Number) aiResponse.getOrDefault("latency_ms", 0)).intValue();

        Message assistantMessage = new Message();
        assistantMessage.setConversationId(conversation.getId());
        assistantMessage.setRole(Message.Role.ASSISTANT);
        assistantMessage.setContent(answer);
        assistantMessage.setAgentUsed(grounded ? "RESEARCH" : "NONE");
        assistantMessage.setLatencyMs(latencyMs);
        try {
            assistantMessage.setCitationsJson(objectMapper.writeValueAsString(aiResponse.get("citations")));
        } catch (Exception e) {
            assistantMessage.setCitationsJson("[]");
        }
        messageRepository.save(assistantMessage);

        conversation.setUpdatedAt(java.time.Instant.now());
        conversationRepository.save(conversation);

        ChatResponse response = new ChatResponse();
        response.conversationId = conversation.getId();
        response.answer = answer;
        response.grounded = grounded;
        response.faithfulnessScore = faithfulness;
        response.latencyMs = latencyMs;
        response.citations = parseCitations(aiResponse.get("citations"));
        return response;
    }

    @SuppressWarnings("unchecked")
    private List<Citation> parseCitations(Object rawCitations) {
        if (rawCitations == null) return List.of();
        List<Map<String, Object>> rawList = (List<Map<String, Object>>) rawCitations;
        return rawList.stream().map(m -> {
            Citation c = new Citation();
            c.index = ((Number) m.get("index")).intValue();
            c.document = (String) m.get("document");
            c.page = ((Number) m.get("page")).intValue();
            c.section = (String) m.get("section");
            c.rerankScore = ((Number) m.get("rerank_score")).doubleValue();
            return c;
        }).toList();
    }

    private Conversation resolveConversation(Long userId, Long conversationId, String firstMessage) {
        if (conversationId != null) {
            return conversationRepository.findByIdAndUserId(conversationId, userId)
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Conversation not found"));
        }
        Conversation conversation = new Conversation();
        conversation.setUserId(userId);
        conversation.setTitle(firstMessage.length() > 60 ? firstMessage.substring(0, 60) + "..." : firstMessage);
        return conversationRepository.save(conversation);
    }

    public List<Conversation> listForUser(Long userId) {
        return conversationRepository.findByUserIdOrderByUpdatedAtDesc(userId);
    }

    public List<Message> getMessages(Long userId, Long conversationId) {
        conversationRepository.findByIdAndUserId(conversationId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Conversation not found"));
        return messageRepository.findByConversationIdOrderByCreatedAtAsc(conversationId);
    }
}
