"""SeqHT: Sequency Hierarchy Truncation


[truncated]
    
    def depth_truncation(self, max_depth: int) -> None:
        """Truncate based on circuit depth."""
        if self.circuit.depth() > max_depth:
            # Remove gates from end
            pass
