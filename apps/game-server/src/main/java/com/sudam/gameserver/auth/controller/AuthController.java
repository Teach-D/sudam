package com.sudam.gameserver.auth.controller;

import com.sudam.gameserver.auth.domain.User;
import com.sudam.gameserver.auth.dto.AuthResponse;
import com.sudam.gameserver.auth.dto.DeleteAccountRequest;
import com.sudam.gameserver.auth.dto.LoginRequest;
import com.sudam.gameserver.auth.dto.SignupRequest;
import com.sudam.gameserver.auth.dto.TokenRefreshRequest;
import com.sudam.gameserver.auth.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.CREATED)
    public AuthResponse signup(@Valid @RequestBody SignupRequest req) {
        return authService.signup(req);
    }

    @PostMapping("/login")
    public AuthResponse login(@Valid @RequestBody LoginRequest req) {
        return authService.login(req);
    }

    @PostMapping("/refresh")
    public AuthResponse refresh(@Valid @RequestBody TokenRefreshRequest req) {
        return authService.refresh(req.refreshToken());
    }

    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void logout(@AuthenticationPrincipal UUID userId) {
        authService.logout(userId);
    }

    @DeleteMapping("/account")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteAccount(@AuthenticationPrincipal UUID userId,
                              @Valid @RequestBody DeleteAccountRequest req) {
        authService.deleteAccount(userId, req.password());
    }

    @GetMapping("/me")
    public ResponseEntity<Map<String, Object>> me(@AuthenticationPrincipal UUID userId) {
        User user = authService.getUser(userId);
        return ResponseEntity.ok(Map.of(
                "id", user.getId(),
                "email", user.getEmail(),
                "nickname", user.getNickname() != null ? user.getNickname() : "",
                "createdAt", user.getCreatedAt()
        ));
    }
}
