"""
Tests for the sample/poster file names of audio and video files. These names are the cache keys under which
generated samples are stored, so a change to their layout orphans every sample generated so far.
Pure string arithmetic on unsaved model instances — no ffmpeg, no storage, no database.
"""
import pytest

from finder.contrib.audio.models import SAMPLE_DURATION, AudioFileModel
from finder.contrib.video.models import VideoFileModel


class TestAudioSamplePath:
    def test_sample_start_and_duration_are_encoded_in_tenths(self):
        audio = AudioFileModel(file_name='song.mp3')
        assert audio.get_sample_path(1.5, 5) == 'song__15_50.mp3'

    def test_start_at_the_beginning(self):
        audio = AudioFileModel(file_name='song.mp3')
        assert audio.get_sample_path(0, SAMPLE_DURATION) == 'song__0_50.mp3'

    def test_fractions_below_a_tenth_are_truncated(self):
        audio = AudioFileModel(file_name='song.ogg')
        assert audio.get_sample_path(1.04, 2.29) == 'song__10_22.ogg'

    def test_keeps_the_suffix_of_the_stored_file(self):
        audio = AudioFileModel(file_name='song.with.dots.wav')
        assert audio.get_sample_path(2, 4) == 'song.with.dots__20_40.wav'

    @pytest.mark.parametrize('start, duration', [(0, 5), (1.5, 5), (1.5, 10)])
    def test_distinct_parameters_yield_distinct_names(self, start, duration):
        audio = AudioFileModel(file_name='song.mp3')
        assert audio.get_sample_path(start, duration) != audio.get_sample_path(3, 7)


class TestVideoSamplePath:
    def test_sample_start_is_encoded_in_hundredths(self):
        video = VideoFileModel(file_name='clip.mp4')
        assert video.get_sample_path(2.5) == 'clip__250.mp4'

    def test_poster_uses_the_given_suffix(self):
        """The poster image of a video is stored next to the sample, but as JPEG."""
        video = VideoFileModel(file_name='clip.mp4')
        assert video.get_sample_path(2.5, suffix='.jpg') == 'clip__250.jpg'

    def test_start_at_the_beginning(self):
        video = VideoFileModel(file_name='clip.mp4')
        assert video.get_sample_path(0) == 'clip__0.mp4'

    def test_fractions_below_a_hundredth_are_truncated(self):
        video = VideoFileModel(file_name='clip.mp4')
        assert video.get_sample_path(1.004) == 'clip__100.mp4'

    def test_keeps_the_suffix_of_the_stored_file(self):
        video = VideoFileModel(file_name='clip.with.dots.mp4')
        assert video.get_sample_path(1) == 'clip.with.dots__100.mp4'


class TestSampleUrlWithoutSampleStart:
    """Without a `sample_start` in the meta data there is nothing to generate, and neither model may touch
    ffmpeg or the storage."""

    def test_video_without_sample_start_falls_back(self):
        video = VideoFileModel(file_name='clip.mp4', meta_data={})
        assert video.get_sample_url(ambit=None) is None
        assert video.get_thumbnail_url(ambit=None) == VideoFileModel.fallback_thumbnail_url
