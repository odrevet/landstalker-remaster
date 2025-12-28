import sys
import argparse
from game import Game

def main() -> None:
    # Initialize argument parser
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="LandStalker")
    parser.add_argument('-r', '--room', type=int, default=1, help='Room number')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('-x', type=float, default=0.0, help='Hero starting X position')
    parser.add_argument('-y', type=float, default=0.0, help='Hero starting Y position')
    parser.add_argument('-z', type=float, default=0.0, help='Hero starting Z position')
    parser.add_argument('-f', '--fullscreen', action='store_true', help='Starts fullscreen')
    parser.add_argument('-W', '--width', type=int, default=320, help='Window width (default: 320)')
    parser.add_argument('-H', '--height', type=int, default=224, help='Window height (default: 224)')
    parser.add_argument('--resizable', action='store_true', default=True, help='Make window resizable (default: True)')
    parser.add_argument('--no-resizable', dest='resizable', action='store_false', help='Disable window resizing')
    parser.add_argument('--scale', type=int, default=1, choices=[1, 2, 3, 4], 
                       help='Display scale multiplier (1-4, default: 1)')
    
    # Display resolution (game rendering resolution / zoom level)
    parser.add_argument('--display-width', type=int, default=320, 
                       help='Game display width - controls zoom level (default: 320)')
    parser.add_argument('--display-height', type=int, default=224, 
                       help='Game display height - controls zoom level (default: 224)')
    
    args: argparse.Namespace = parser.parse_args()
    
    # Create and run game
    game: Game = Game(args)
    game.run()

if __name__ == "__main__":
    main()