package com.researchmind.controller;

import com.researchmind.dto.ChatDtos.ChatRequest;
import com.researchmind.dto.ChatDtos.ChatResponse;
import com.researchmind.entity.Conversation;
import com.researchmind.entity.Message;
import com.researchmind.service.ChatService;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping("/chat")
    public ChatResponse chat(@AuthenticationPrincipal Long userId, @RequestBody ChatRequest request) {
        return chatService.chat(userId, request);
    }

    @GetMapping("/conversations")
    public List<Conversation> listConversations(@AuthenticationPrincipal Long userId) {
        return chatService.listForUser(userId);
    }

    @GetMapping("/conversations/{id}")
    public List<Message> getConversationMessages(@AuthenticationPrincipal Long userId, @PathVariable Long id) {
        return chatService.getMessages(userId, id);
    }
}
