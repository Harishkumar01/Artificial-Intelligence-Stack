#create an mcp agent
class MCPAgent:
    def __init__(self, name, role):
        self.name = name
        self.role = role

    def perform_task(self, task):
        print(f"{self.name} is performing the task: {task}")

    def communicate(self, message):
        print(f"{self.name} says: {message}")

    def get_role(self):
        return self.role


if __name__ == "__main__":
    # Example usage
    agent1 = MCPAgent("Agent1", "Coordinator")
    agent2 = MCPAgent("Agent2", "Worker")

    agent1.perform_task("Coordinate the workflow")
    agent2.perform_task("Execute the assigned task")

    agent1.communicate("Please provide the status update.")
    agent2.communicate("Task completed successfully.")

    print(f"{agent1.name} has the role: {agent1.get_role()}")
    print(f"{agent2.name} has the role: {agent2.get_role()}")