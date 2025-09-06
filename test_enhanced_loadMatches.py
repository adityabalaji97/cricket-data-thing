#!/usr/bin/env python3
"""
Unit tests for Enhanced Match Loader
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
import os
from pathlib import Path
from enhanced_loadMatches import EnhancedMatchLoader
from models import Match, Delivery, Player

class TestEnhancedMatchLoader(unittest.TestCase):
    """Test cases for EnhancedMatchLoader"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the database connection
        with patch('enhanced_loadMatches.get_database_connection') as mock_db:
            mock_engine = Mock()
            mock_session_class = Mock()
            mock_db.return_value = (mock_engine, mock_session_class)
            
            self.loader = EnhancedMatchLoader(auto_create_players=True, batch_size=10)
            self.mock_session = Mock()
            self.loader.SessionLocal.return_value = self.mock_session
    
    def test_calculate_crease_combo(self):
        """Test crease combination calculation"""
        # Test known combinations
        self.assertEqual(self.loader._calculate_crease_combo('RHB', 'RHB'), 'rhb_rhb')
        self.assertEqual(self.loader._calculate_crease_combo('LHB', 'LHB'), 'lhb_lhb')
        self.assertEqual(self.loader._calculate_crease_combo('RHB', 'LHB'), 'lhb_rhb')
        self.assertEqual(self.loader._calculate_crease_combo('LHB', 'RHB'), 'lhb_rhb')
        
        # Test unknown cases
        self.assertEqual(self.loader._calculate_crease_combo('unknown', 'RHB'), 'unknown')
        self.assertEqual(self.loader._calculate_crease_combo('RHB', 'unknown'), 'unknown')
    
    def test_calculate_ball_direction(self):
        """Test ball direction calculation"""
        # Test into batter cases
        self.assertEqual(self.loader._calculate_ball_direction('RHB', 'RO'), 'intoBatter')
        self.assertEqual(self.loader._calculate_ball_direction('RHB', 'LC'), 'intoBatter')
        self.assertEqual(self.loader._calculate_ball_direction('LHB', 'RL'), 'intoBatter')
        self.assertEqual(self.loader._calculate_ball_direction('LHB', 'LO'), 'intoBatter')
        
        # Test away from batter cases
        self.assertEqual(self.loader._calculate_ball_direction('LHB', 'RO'), 'awayFromBatter')
        self.assertEqual(self.loader._calculate_ball_direction('LHB', 'LC'), 'awayFromBatter')
        self.assertEqual(self.loader._calculate_ball_direction('RHB', 'RL'), 'awayFromBatter')
        self.assertEqual(self.loader._calculate_ball_direction('RHB', 'LO'), 'awayFromBatter')
        
        # Test unknown cases
        self.assertEqual(self.loader._calculate_ball_direction('unknown', 'RO'), 'unknown')
        self.assertEqual(self.loader._calculate_ball_direction('RHB', 'unknown'), 'unknown')
    
    def test_get_player_info(self):
        """Test player info retrieval from cache"""
        # Setup cache
        self.loader.player_cache = {
            'Test Player': {
                'batter_type': 'RHB',
                'bowler_type': 'RF'
            }
        }
        
        # Test existing player
        info = self.loader._get_player_info('Test Player')
        self.assertEqual(info['batter_type'], 'RHB')
        self.assertEqual(info['bowler_type'], 'RF')
        
        # Test non-existing player
        info = self.loader._get_player_info('Unknown Player')
        self.assertEqual(info['batter_type'], 'unknown')
        self.assertEqual(info['bowler_type'], 'unknown')
    
    def create_sample_json_data(self, match_id: str = 'test_match') -> dict:
        """Create sample JSON match data for testing"""
        return {
            'info': {
                'dates': ['2024-01-01'],
                'teams': ['Team A', 'Team B'],
                'venue': 'Test Stadium',
                'city': 'Test City',
                'toss': {
                    'winner': 'Team A',
                    'decision': 'bat'
                },
                'outcome': {
                    'winner': 'Team A'
                },
                'overs': 20,
                'balls_per_over': 6,
                'event': {
                    'name': 'Test Tournament',
                    'match_number': 1
                }
            },
            'innings': [
                {
                    'team': 'Team A',
                    'overs': [
                        {
                            'over': 0,
                            'deliveries': [
                                {
                                    'batter': 'Player A',
                                    'non_striker': 'Player B',
                                    'bowler': 'Player C',
                                    'runs': {'batter': 1, 'extras': 0}
                                },
                                {
                                    'batter': 'Player A',
                                    'non_striker': 'Player B',
                                    'bowler': 'Player C',
                                    'runs': {'batter': 4, 'extras': 0}
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    
    def test_create_enhanced_delivery(self):
        """Test creation of enhanced delivery with all columns"""
        # Setup player cache
        self.loader.player_cache = {
            'Player A': {'batter_type': 'RHB', 'bowler_type': 'RF'},
            'Player B': {'batter_type': 'LHB', 'bowler_type': 'RM'},
            'Player C': {'batter_type': 'RHB', 'bowler_type': 'RO'}
        }
        
        ball_data = {
            'batter': 'Player A',
            'non_striker': 'Player B',
            'bowler': 'Player C',
            'runs': {'batter': 4, 'extras': 0}
        }
        
        match_context = {
            'match_id': 'test_match',
            'innings': 1,
            'over': 0,
            'ball': 1,
            'batting_team': 'Team A',
            'bowling_team': 'Team B'
        }
        
        delivery = self.loader.create_enhanced_delivery(ball_data, match_context)
        
        # Verify basic fields
        self.assertEqual(delivery.match_id, 'test_match')
        self.assertEqual(delivery.batter, 'Player A')
        self.assertEqual(delivery.non_striker, 'Player B')
        self.assertEqual(delivery.bowler, 'Player C')
        self.assertEqual(delivery.runs_off_bat, 4)
        
        # Verify enhancement fields
        self.assertEqual(delivery.striker_batter_type, 'RHB')
        self.assertEqual(delivery.non_striker_batter_type, 'LHB')
        self.assertEqual(delivery.bowler_type, 'RO')
        
        # Verify derived fields
        self.assertEqual(delivery.crease_combo, 'lhb_rhb')  # RHB + LHB
        self.assertEqual(delivery.ball_direction, 'intoBatter')  # RHB vs RO
    
    @patch('enhanced_loadMatches.PlayerDiscoveryService')
    def test_ensure_players_exist(self, mock_discovery_service):
        """Test ensuring players exist functionality"""
        # Mock player discovery service
        mock_service_instance = Mock()
        mock_discovery_service.return_value = mock_service_instance
        
        # Mock discovered players
        mock_service_instance.scan_single_file_for_players.return_value = {
            'New Player': Mock(name='New Player')
        }
        mock_service_instance.find_missing_players.return_value = {
            'New Player': Mock(name='New Player')
        }
        mock_service_instance.create_placeholder_players.return_value = 1
        
        # Re-initialize loader with mocked service
        self.loader.player_discovery = mock_service_instance
        
        # Test
        created_count = self.loader.ensure_players_exist('test.json', self.mock_session)
        
        # Verify calls
        mock_service_instance.scan_single_file_for_players.assert_called_once_with('test.json')
        mock_service_instance.find_missing_players.assert_called_once()
        mock_service_instance.create_placeholder_players.assert_called_once()
        
        self.assertEqual(created_count, 1)
    
    def test_load_player_cache(self):
        """Test loading player cache from database"""
        # Mock database query
        mock_players = [
            ('Player A', 'RHB', 'RF'),
            ('Player B', 'LHB', 'RM'),
            ('Player C', None, 'RO')  # Test null handling
        ]
        self.mock_session.query.return_value.all.return_value = mock_players
        
        # Load cache
        self.loader._load_player_cache(self.mock_session)
        
        # Verify cache content
        self.assertTrue(self.loader.cache_loaded)
        self.assertEqual(len(self.loader.player_cache), 3)
        
        # Test specific entries
        self.assertEqual(self.loader.player_cache['Player A']['batter_type'], 'RHB')
        self.assertEqual(self.loader.player_cache['Player A']['bowler_type'], 'RF')
        
        # Test null handling
        self.assertEqual(self.loader.player_cache['Player C']['batter_type'], 'unknown')
        self.assertEqual(self.loader.player_cache['Player C']['bowler_type'], 'RO')
    
    def test_get_existing_match_ids(self):
        """Test getting existing match IDs from database"""
        # Mock database query
        mock_ids = [('match1',), ('match2',), ('match3',)]
        self.mock_session.query.return_value.all.return_value = mock_ids
        
        # Get existing IDs
        existing_ids = self.loader.get_existing_match_ids(self.mock_session)
        
        # Verify result
        self.assertEqual(existing_ids, {'match1', 'match2', 'match3'})

if __name__ == '__main__':
    unittest.main()
