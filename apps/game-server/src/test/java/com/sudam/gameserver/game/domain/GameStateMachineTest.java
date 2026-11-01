package com.sudam.gameserver.game.domain;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.*;

class GameStateMachineTest {

    private Game game;

    @BeforeEach
    void setUp() {
        game = Game.create(19, 6.5f);
    }

    @Test
    void waiting_to_playing_on_start() {
        assertThat(game.getStatus()).isEqualTo(GameStatus.WAITING);
        game.start();
        assertThat(game.getStatus()).isEqualTo(GameStatus.PLAYING);
    }

    @Test
    void playing_to_coach_pause() {
        game.start();
        game.pauseForCoach();
        assertThat(game.getStatus()).isEqualTo(GameStatus.COACH_PAUSE);
        assertThat(game.isClockPaused()).isTrue();
    }

    @Test
    void coach_pause_to_answering() {
        game.start();
        game.pauseForCoach();
        game.startAnswering();
        assertThat(game.getStatus()).isEqualTo(GameStatus.ANSWERING);
    }

    @Test
    void coach_pause_to_playing_via_resume() {
        game.start();
        game.pauseForCoach();
        game.resume();
        assertThat(game.getStatus()).isEqualTo(GameStatus.PLAYING);
        assertThat(game.isClockPaused()).isFalse();
    }

    @Test
    void answering_to_playing_via_resume() {
        game.start();
        game.pauseForCoach();
        game.startAnswering();
        game.resume();
        assertThat(game.getStatus()).isEqualTo(GameStatus.PLAYING);
        assertThat(game.isClockPaused()).isFalse();
    }

    @Test
    void playing_to_finished() {
        game.start();
        game.finish();
        assertThat(game.getStatus()).isEqualTo(GameStatus.FINISHED);
    }

    @Test
    void pause_from_non_playing_throws() {
        game.start();
        game.pauseForCoach();
        assertThatThrownBy(game::pauseForCoach)
                .isInstanceOf(IllegalStateException.class);
    }

    @Test
    void resume_from_playing_throws() {
        game.start();
        assertThatThrownBy(game::resume)
                .isInstanceOf(IllegalStateException.class);
    }

    @Test
    void start_answering_from_playing_throws() {
        game.start();
        assertThatThrownBy(game::startAnswering)
                .isInstanceOf(IllegalStateException.class);
    }

    @Test
    void clock_paused_during_coach_pause() {
        game.start();
        assertThat(game.isClockPaused()).isFalse();
        game.pauseForCoach();
        assertThat(game.isClockPaused()).isTrue();
    }

    @Test
    void clock_paused_remains_during_answering() {
        game.start();
        game.pauseForCoach();
        game.startAnswering();
        assertThat(game.isClockPaused()).isTrue();
    }

    @Test
    void clock_resumes_after_resume() {
        game.start();
        game.pauseForCoach();
        game.resume();
        assertThat(game.isClockPaused()).isFalse();
    }

    @Test
    void increment_move_count() {
        game.start();
        assertThat(game.getMoveCount()).isEqualTo(0);
        game.incrementMoveCount();
        game.incrementMoveCount();
        assertThat(game.getMoveCount()).isEqualTo(2);
    }
}
