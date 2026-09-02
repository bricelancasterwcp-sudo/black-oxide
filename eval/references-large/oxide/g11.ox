fn strided_sum(grid: Vec<Int>, start: Int, step: Int, count: Int) -> Int {
    let total = 0
    for k in range(0, count) {
        total += grid[start + k * step]
    }
    total
}

fn main() {
    let grid = vec().push(4).push(9).push(2).push(3).push(5).push(7).push(8).push(1).push(6)
    let size = 3
    let sums = vec()
    for r in range(0, size) {
        let s = strided_sum(grid, r * size, 1, size)
        print(s)
        sums = push(sums, s)
    }
    for c in range(0, size) {
        let s = strided_sum(grid, c, size, size)
        print(s)
        sums = push(sums, s)
    }
    let diagonal = strided_sum(grid, 0, size + 1, size)
    let anti = strided_sum(grid, size - 1, size - 1, size)
    print(diagonal)
    print(anti)
    let magic = anti == diagonal
    for s in sums {
        if s != diagonal {
            magic = false
        }
    }
    print(magic)
}
