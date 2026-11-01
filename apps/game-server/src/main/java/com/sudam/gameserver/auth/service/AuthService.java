package com.sudam.gameserver.auth.service;

import com.sudam.gameserver.auth.domain.RefreshToken;
import com.sudam.gameserver.auth.domain.User;
import com.sudam.gameserver.auth.dto.AuthResponse;
import com.sudam.gameserver.auth.dto.LoginRequest;
import com.sudam.gameserver.auth.dto.SignupRequest;
import com.sudam.gameserver.auth.repository.RefreshTokenRepository;
import com.sudam.gameserver.auth.repository.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.Base64;
import java.util.HexFormat;
import java.util.NoSuchElementException;
import java.util.UUID;

@Service
@Transactional
public class AuthService {

    private final UserRepository users;
    private final RefreshTokenRepository refreshTokens;
    private final JwtService jwt;
    private final PasswordEncoder passwordEncoder;
    private final long refreshExpirationMs;

    public AuthService(UserRepository users,
                       RefreshTokenRepository refreshTokens,
                       JwtService jwt,
                       PasswordEncoder passwordEncoder,
                       @Value("${jwt.refresh-expiration-ms}") long refreshExpirationMs) {
        this.users = users;
        this.refreshTokens = refreshTokens;
        this.jwt = jwt;
        this.passwordEncoder = passwordEncoder;
        this.refreshExpirationMs = refreshExpirationMs;
    }

    public AuthResponse signup(SignupRequest req) {
        if (users.existsByEmail(req.email())) {
            throw new IllegalArgumentException("Email already registered");
        }
        String hash = passwordEncoder.encode(req.password());
        User user = users.save(User.create(req.email(), hash, req.nickname()));
        return issueTokens(user);
    }

    public AuthResponse login(LoginRequest req) {
        User user = users.findByEmail(req.email())
                .orElseThrow(() -> new IllegalArgumentException("Invalid credentials"));
        if (!passwordEncoder.matches(req.password(), user.getPasswordHash())) {
            throw new IllegalArgumentException("Invalid credentials");
        }
        return issueTokens(user);
    }

    public AuthResponse refresh(String rawRefreshToken) {
        String hash = sha256(rawRefreshToken);
        RefreshToken rt = refreshTokens.findByTokenHash(hash)
                .orElseThrow(() -> new IllegalArgumentException("Invalid refresh token"));
        if (rt.isExpired()) {
            refreshTokens.delete(rt);
            throw new IllegalArgumentException("Refresh token expired");
        }
        refreshTokens.delete(rt);
        return issueTokens(rt.getUser());
    }

    public void logout(UUID userId) {
        refreshTokens.deleteAllByUserId(userId);
    }

    @Transactional(readOnly = true)
    public User getUser(UUID userId) {
        return users.findById(userId)
                .orElseThrow(() -> new NoSuchElementException("User not found: " + userId));
    }

    private AuthResponse issueTokens(User user) {
        String accessToken = jwt.generateAccessToken(user.getId(), user.getEmail());
        String rawRefresh = UUID.randomUUID().toString();
        LocalDateTime expiresAt = LocalDateTime.now().plusSeconds(refreshExpirationMs / 1000);
        refreshTokens.save(RefreshToken.create(user, sha256(rawRefresh), expiresAt));
        return new AuthResponse(accessToken, rawRefresh, user.getId(), user.getEmail(), user.getNickname());
    }

    private static String sha256(String input) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(input.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
