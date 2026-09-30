package com.researchmind.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public class AuthDtos {

    public static class RegisterRequest {
        @Email @NotBlank
        public String email;

        @NotBlank @Size(min = 8, message = "Password must be at least 8 characters")
        public String password;

        public String displayName;
    }

    public static class LoginRequest {
        @Email @NotBlank
        public String email;

        @NotBlank
        public String password;
    }

    public static class AuthResponse {
        public String token;
        public long expiresAt;
        public Long userId;
        public String email;

        public AuthResponse(String token, long expiresAt, Long userId, String email) {
            this.token = token;
            this.expiresAt = expiresAt;
            this.userId = userId;
            this.email = email;
        }
    }
}
