import numpy as np
from typing import NamedTuple, Sequence, Union
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

class DDMParameters(NamedTuple):
    w1a: float
    w1b: float
    w2: float
    w3: float
    w4: float
    w5: float
    
class DetourDistributionInference:
    def __init__(self, cost_matrix: np.ndarray, ddm_params: DDMParameters, lc_indices: Sequence[int], lc_sizes: Sequence[int]) -> None:
        self.lc_size_factors = ddm_params.w5 * np.log(lc_sizes)
        self.cost_matrix = cost_matrix
        self.lc_indices = lc_indices
        self.lc_sizes = lc_sizes
        self.w1a = ddm_params.w1a
        self.w1b = ddm_params.w1b
        self.w2 = ddm_params.w2
        self.w3 = ddm_params.w3
        self.w4 = ddm_params.w4
        self.w5 = ddm_params.w5
        self.temperature = 5.0

    def sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Compute sigmoid function."""
        return 1 / (1 + np.exp(-x))

    def softmax(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Compute softmax values."""
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)

    def logsumexp(self, x: np.ndarray, axis: int = -1) -> np.ndarray:
        """Compute log sum exp."""
        max_x = np.max(x, axis=axis, keepdims=True)
        return np.log(np.sum(np.exp(x - max_x), axis=axis)) + np.squeeze(max_x)

    def compute_weighted(self, origin_indices: Union[Sequence[int], np.ndarray] = None, 
                        destination_indices: Union[Sequence[int], np.ndarray] = None) -> np.ndarray:
        """Compute weighted detour and direct costs for given origins and destinations."""
        k = self.lc_indices.shape[0]
        
        # Expand dimensions for broadcasting
        o_idx_exp = np.expand_dims(origin_indices, axis=1) # Shape: (n, 1)
        d_idx_exp = np.expand_dims(destination_indices, axis=1) # Shape: (n, 1)
        lc_exp = np.broadcast_to(self.lc_indices, (len(origin_indices), k)) # Shape: (n, k)
        
        # weighted costs for k logistics centers
        detour_size_factor = (self.sigmoid(self.w1a) * self.cost_matrix[o_idx_exp, lc_exp] +
                 self.sigmoid(self.w1b) * self.cost_matrix[lc_exp, d_idx_exp] +
                 self.w2) + self.lc_size_factors # Shape: (n, k)
        
        # direct cost with no scaling
        direct = self.sigmoid(self.w3) * self.cost_matrix[origin_indices, destination_indices] + self.w4
        
        # combine detour and direct
        return np.concatenate([detour_size_factor, np.expand_dims(direct, axis=1)], axis=1)

    def forward(self, probs_indices: np.ndarray) -> np.ndarray:
        # compute only for origins with data
        origin_set = probs_indices[:,0]
        # compute only for destination with data
        destination_set = probs_indices[:,1]
        
        weighted = self.compute_weighted(origin_indices=origin_set, destination_indices=destination_set)
        
        # Now you have 2 top-level utilities: direct_cost vs. detour_utility
        top_level_utilities = np.stack([-weighted[:, -1] / self.temperature, self.logsumexp(-weighted[:, :-1] / self.temperature, axis=1)], axis=1)
        p_top = self.softmax(top_level_utilities, axis=1)
        
        # Combine into final choice probabilities
        p_direct = np.expand_dims(p_top[:, 0], axis=1)
        p_detour = np.expand_dims(p_top[:, 1], axis=1) * self.softmax(-weighted[:, :-1] / self.temperature, axis=1)
        
        probs_batch = np.concatenate([p_detour, p_direct], axis=1)
        return probs_batch
    
def process_batch(args):
    """Process a single batch of origins."""
    origin_offset, batch_size, n, k_plus1, model, demand, lcs, final_demand, total_per_route, lock = args
    
    B = min(batch_size, n - origin_offset)
    
    # Create indices using meshgrid
    origin_indices = np.arange(origin_offset, origin_offset + B, dtype=np.int32)
    dest_indices = np.arange(n, dtype=np.int32)
    o_grid, d_grid = np.meshgrid(origin_indices, dest_indices, indexing='ij')
    eval_indices = np.stack([o_grid.ravel(), d_grid.ravel()], axis=1)
    
    # Get probabilities and reshape
    probs_batch_flat = model.forward(probs_indices=eval_indices)
    probs_batch = probs_batch_flat.reshape(B, n, k_plus1)
    
    # Get demand batch and expand dimensions
    demand_batch = demand[origin_offset:origin_offset+B, :, np.newaxis]
    
    # Compute distribution using broadcasting
    dist_batch = demand_batch * probs_batch
    
    # Process detours and compute updates
    detours = dist_batch[:, :, :-1]
    direct = dist_batch[:, :, -1]
    orig_to_c = np.sum(detours, axis=1)
    c_to_dest = np.sum(detours, axis=0)
    route_totals = np.sum(dist_batch, axis=(0, 1))
    
    # Update shared arrays with lock to ensure thread safety
    with lock:
        final_demand[origin_offset:origin_offset+B, lcs] += orig_to_c
        final_demand[lcs] += c_to_dest.T
        final_demand[origin_offset:origin_offset+B, :] += direct
        total_per_route += route_totals
    
    return origin_offset, B

def process_logistics_inference(model: DetourDistributionInference, n_zones: int, demand: np.ndarray) -> None:

    # Process full matrix in origin batches to limit memory usage
    # Process full matrix in origin batches in parallel
    k_plus1 = len(model.lc_indices) + 1
    batch_size = 15
    final_demand = np.zeros((n_zones, n_zones), dtype=np.float32)
    total_per_route = np.zeros((k_plus1,), dtype=np.float32)
    lock = Lock()
    
    # Create list of batch arguments including shared arrays
    batch_args = [
        (offset, batch_size, n_zones, k_plus1, model, demand, model.lc_indices, final_demand, total_per_route, lock)
        for offset in range(0, n_zones, batch_size)
    ]
    
    # Process batches in parallel
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = list(executor.map(process_batch, batch_args))
    
    # after processing all batches
    detour_total = np.sum(total_per_route[:-1])
    direct_total = total_per_route[-1]
    print(f"Total demand via logistics centers: {detour_total:.4f}")
    print(f"Total direct demand: {direct_total:.4f}")
    
    print("Final demand matrix including detour legs and direct:")
    print(f'orig_demand: {np.sum(demand)}, final_demand: {np.sum(final_demand)}')

    # output the final demand matrix
    return final_demand
